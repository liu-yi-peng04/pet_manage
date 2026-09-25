from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse

from app.api.auth import get_current_user
from app.api.knowledge_base import find_kb
from app.core.config import get_settings
from app.models.models import ChatMessage, Conversation, KnowledgeBase, User
from app.schemas.schemas import ChatMessageIn, ChatMessageOut
from app.services import agent_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _chat_channel(user: User) -> str:
    """各端 AI 独立通道，会话与历史互不可见。"""
    role = (user.role or "user").strip().lower()
    if role in ("staff", "admin", "operator", "trainer"):
        return role
    return "user"


async def _resolve_chat_context(kb_id: int | None, user: User, consult_type: str | None):
    """consult_type=pet 走公共养宠顾问；policy 走门店/公司制度。"""
    settings = get_settings()
    mode_hint = (consult_type or "").strip().lower()
    # 商家端默认制度助手；养宠用户默认养宠顾问
    if mode_hint not in ("pet", "policy"):
        if user.role == "staff":
            mode_hint = "policy"
        else:
            mode_hint = "policy" if kb_id is not None else "pet"

    if mode_hint == "pet":
        # 商家没有「自家宠物」档案，禁止走用户宠顾问上下文
        if user.role == "staff":
            raise HTTPException(status_code=400, detail="商家端请使用店内制度助手，养宠问答仅对用户开放")
        public = await KnowledgeBase.filter(is_public=True, name=settings.PUBLIC_KB_NAME).first()
        if not public:
            public = await KnowledgeBase.filter(is_public=True).first()
        return public, "public", None

    if kb_id is not None:
        kb = await find_kb(kb_id, user)
        return kb, "store", kb.store_id
    if user.role == "staff" and user.store_id:
        kb = await KnowledgeBase.filter(store_id=user.store_id).first()
        return kb, "store", user.store_id
    if kb_id is None:
        public = await KnowledgeBase.filter(is_public=True).first()
        return public, "public", None
    kb = await find_kb(kb_id, user)
    return kb, "store" if kb.store_id else "public", kb.store_id


async def _pet_prompt_addon(user: User, pet_id: int | None, agent_mode: str) -> str:
    if agent_mode == "store":
        return ""
    if user.role == "staff":
        return ""
    if not pet_id:
        return (
            "\n用户尚未在问答页绑定宠物。给出个性化喂养/用药/运动方案前，"
            "请提醒先去「我的宠物」建档或在下拉框选择；同名宠物必须用昵称/品种/生日区分。"
        )
    from app.api.pets import pet_profile_for_agent

    ctx = await pet_profile_for_agent(user, pet_id)
    import json

    return (
        "\n当前绑定宠物档案（含疫苗/体检/用药）如下，个性化方案必须基于此，"
        "尤其注意过敏、慢性病、月龄与体重，不要张冠李戴：\n"
        + json.dumps(ctx, ensure_ascii=False)
    )


async def _prepare(
    kb_id: int | None,
    content: str,
    conversation_id: int | None,
    user: User,
    pet_id: int | None,
    consult_type: str | None,
):
    channel = _chat_channel(user)
    kb, agent_mode, store_id = await _resolve_chat_context(kb_id, user, consult_type)
    kb_id_final = kb.id if kb is not None else None

    # 仅复用「同用户 + 同端」会话，避免跨端串话
    conv = None
    if conversation_id:
        conv = await Conversation.get_or_none(id=conversation_id, user=user, channel=channel)
    if conv is None:
        conv = await Conversation.create(
            user=user, kb=kb, title=content[:30], channel=channel
        )
    elif getattr(conv, "channel", None) != channel:
        conv = await Conversation.create(
            user=user, kb=kb, title=content[:30], channel=channel
        )

    await ChatMessage.create(conversation=conv, role="user", content=content)
    history_msgs = await ChatMessage.filter(conversation=conv).order_by("id")
    history = [{"role": m.role, "content": m.content} for m in history_msgs][:-1]
    # 商家端不带用户宠物档案
    safe_pet_id = None if user.role == "staff" else pet_id
    pet_addon = await _pet_prompt_addon(user, safe_pet_id, agent_mode)
    return conv, history, kb_id_final, agent_mode, store_id, safe_pet_id, pet_addon


def _agent_messages(
    content: str,
    history: list[dict] | None = None,
    agent_mode: str = "public",
    pet_addon: str = "",
):
    prompt = (
        agent_service.STORE_SYSTEM_PROMPT
        if agent_mode == "store"
        else agent_service.AGENT_SYSTEM_PROMPT
    )
    prompt += pet_addon
    return [
        {"role": "system", "content": prompt},
        *(history or []),
        {"role": "user", "content": content},
    ]


@router.post("", response_model=ChatMessageOut)
async def chat(
    data: ChatMessageIn,
    user: User = Depends(get_current_user),
):
    conv, history, kb_id, agent_mode, store_id, pet_id, pet_addon = await _prepare(
        data.kb_id, data.content, data.conversation_id, user, data.pet_id, data.consult_type
    )
    messages = _agent_messages(data.content, history, agent_mode, pet_addon)
    import asyncio

    loop = asyncio.get_event_loop()
    try:
        answer = await run_in_threadpool(
            agent_service.run_agent_last,
            messages,
            kb_id,
            user.id,
            loop,
            pet_id,
            store_id,
            agent_mode,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"大模型调用失败: {e}")

    reply = await ChatMessage.create(conversation=conv, role="assistant", content=answer)
    return reply


@router.post("/stream")
async def chat_stream(
    data: ChatMessageIn,
    user: User = Depends(get_current_user),
):
    conv, history, kb_id, agent_mode, store_id, pet_id, pet_addon = await _prepare(
        data.kb_id, data.content, data.conversation_id, user, data.pet_id, data.consult_type
    )
    messages = _agent_messages(data.content, history, agent_mode, pet_addon)

    import asyncio
    import json
    import queue

    def sse(obj: dict) -> str:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    async def event_gen():
        collected: list[str] = []
        q: "queue.Queue" = queue.Queue()

        def worker():
            try:
                for ev in agent_service.run_agent(
                    messages, kb_id, user.id, loop, pet_id, store_id, agent_mode
                ):
                    q.put(ev)
            except Exception as e:  # noqa: BLE001
                q.put({"type": "error", "content": str(e)})
            finally:
                q.put({"type": "done"})

        loop = asyncio.get_event_loop()
        yield sse({"type": "conv", "id": conv.id})
        executor = loop.run_in_executor(None, worker)
        try:
            while True:
                try:
                    ev = await asyncio.to_thread(q.get, True, 0.5)
                except queue.Empty:
                    continue
                if ev.get("type") == "done":
                    break
                if ev.get("type") == "tool":
                    yield sse({"type": "tool", "name": ev["name"], "summary": ev["summary"]})
                elif ev.get("type") == "delta":
                    content = ev["content"]
                    collected.append(content)
                    yield sse({"type": "delta", "content": content})
                elif ev.get("type") == "error":
                    yield sse({"type": "error", "content": ev["content"]})
        finally:
            await executor

        full = "".join(collected)
        if full:
            await ChatMessage.create(conversation=conv, role="assistant", content=full)
        yield sse({"type": "done"})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations", response_model=list[ChatMessageOut])
async def list_conversations(user: User = Depends(get_current_user)):
    channel = _chat_channel(user)
    msgs = (
        await ChatMessage.filter(conversation__user=user, conversation__channel=channel)
        .order_by("-id")
        .limit(50)
    )
    return msgs
