"""智能体：基于 DeepSeek Function Calling 的工具调用循环。

流程：把系统提示 + 历史 + 用户问题、以及可用工具定义一次性给 DeepSeek；
若模型返回 tool_calls -> 执行工具 -> 把结果回传给模型 -> 重复；
直到模型返回最终文本回答。
"""
from __future__ import annotations

import json

import httpx

from app.core.config import get_settings
from app.services.vectordb_service import vector_db_service

settings = get_settings()

# 门店内容库检索：仅店端会话启用
STORE_KB_RETRIEVE_TOOL = {
    "type": "function",
    "function": {
        "name": "kb_retrieve",
        "description": (
            "在本店内容库中做向量检索，返回与该问题最相关的店内文档片段"
            "（服务条款、寄养细则、商品说明、护理手册、SOP 等）。"
            "当需要回答店内业务流程、收费/退换规则、本店服务内容时优先使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索关键词或问题"},
            },
            "required": ["query"],
        },
    },
}

# 平台公共养护知识库：C 端宠物管家默认启用
PUBLIC_KB_RETRIEVE_TOOL = {
    "type": "function",
    "function": {
        "name": "kb_retrieve",
        "description": (
            "在平台公共养护知识库中检索（疫苗、喂养、疾病科普、用品选购、寄养常识等）。"
            "回答养宠常识、健康建议、疫苗间隔等通用问题时必须先检索，不要凭记忆编造。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索关键词或问题"},
            },
            "required": ["query"],
        },
    },
}

# DeepSeek 工具定义
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "tavily_search",
            "description": (
                "联网搜索最新专业资料（指南、品种易感病、疫苗间隔、用药注意等）。"
                "在已读取宠物档案后，制定个性化方案前应检索：把品种、年龄、症状写进 query。"
                "知识库没有、或需要核对时效性时必须调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pet_lookup",
            "description": (
                "查询当前用户宠物档案（含昵称、过敏、慢性病、饮食、活动量、居住环境）。"
                "做喂养、运动、医疗、用品建议前必须先查档案；同名时会返回候选列表。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pet_id": {"type": "integer", "description": "宠物 ID（可选）"},
                    "name": {"type": "string", "description": "宠物名（可选，与 pet_id 二选一）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vaccine_schedule",
            "description": (
                "查询当前用户某只宠物的疫苗记录与下次到期日（含已过期/即将到期状态）。"
                "当用户询问自家宠物疫苗情况、下次什么时候打针时使用。"
                "可不传 pet_id：将使用问答页选中的宠物，或用户仅有一只时自动选择。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pet_id": {"type": "integer", "description": "宠物 ID（可选）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "product_query",
            "description": (
                "查询在售宠物商品（笼子/玩具/用品/食品等）。推荐时必须带上门店名称、电话、地址，"
                "引导主人到店咨询/购买。若问自家宠物该买多大笼子/什么规格，应传入 pet_id。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pet_id": {"type": "integer", "description": "宠物 ID（可选，用于按宠物体重匹配规格）"},
                    "category": {
                        "type": "string",
                        "description": "商品分类: cage(笼子)/toy(玩具)/supply(用品)/food(食品)/health(医疗保健)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "health_lookup",
            "description": (
                "查询当前用户某只宠物的体检记录与用药记录。当用户询问自家宠物体检过没有、"
                "体检结果如何、用过什么药、是否在用药时使用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pet_id": {"type": "integer", "description": "宠物 ID（可选）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "match_resources",
            "description": (
                "按用户需求匹配平台合作资源：待售宠物、宠物店、训犬师、宠物医院、寄养中心。"
                "当用户问适合养什么、去哪买、行为训练、附近医院时必须调用。"
                "need_type: buy_pet / product / train / hospital / boarding / consult"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "need_type": {"type": "string"},
                    "species": {"type": "string"},
                    "breed": {"type": "string"},
                    "city": {"type": "string"},
                    "budget": {"type": "number"},
                    "keyword": {"type": "string", "description": "行为问题或关键词，如拆家/乱叫"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_lead",
            "description": (
                "把用户明确的购买/训练/就医需求登记为运营线索，方便服务商跟进获客。"
                "用户表达想被对接时使用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "need_type": {"type": "string"},
                    "summary": {"type": "string", "description": "需求摘要"},
                    "city": {"type": "string"},
                    "budget": {"type": "number"},
                },
                "required": ["summary"],
            },
        },
    },
]

TOOL_NAMES = {t["function"]["name"] for t in TOOLS}

# 系统提示：宠物 AI 管家，只围绕用户自家宠物
AGENT_SYSTEM_PROMPT = (
    "你是『宠智联』的 AI 宠物顾问：根据这只宠物的档案给出可执行方案，再匹配门店/训犬师/医院/商品。"
    "工作顺序（个性化方案题必须遵守）：\n"
    "1. 已注入档案则直接用；缺疫苗/体检/用药时再调 vaccine_schedule、health_lookup。"
    "用户提到名字且可能重名时调 pet_lookup，按候选的昵称/品种/生日请用户确认，不要猜错狗。\n"
    "2. kb_retrieve 公共养护库 → tavily_search 核对最新做法（query 含品种+月龄+问题）。\n"
    "3. 需要买东西/训练/就医时再 match_resources 或 product_query。\n"
    "输出必须是 Markdown，结构如下（可按问题删减，但不要写成一整段）：\n"
    "## 针对 {宠物名} 的建议\n"
    "用 2～4 条要点点明：月龄/体重、过敏与慢性病、当前饮食与活动量。\n"
    "### 个性化方案\n"
    "分 1. 2. 3. 写清剂量/频次/时长；避开过敏原与禁忌。\n"
    "### 依据\n"
    "知识库或网页标题+要点，无出处就写「经验建议」。\n"
    "### 就医红线\n"
    "出现哪些症状必须停在家处理、去医院；不替代兽医诊断。\n"
    "中文、短句、列表优先。不要编造门店、医生、药品批号。"
)

# 门店店端问答的系统提示：会话绑定本店内容库(kb_id 非空)时使用
STORE_SYSTEM_PROMPT = (
    "你是本宠物门店的『店内智能助手』，协助店员处理店内业务、回答顾客咨询。回答遵循：\n"
    "1. 涉及本店服务条款、寄养细则、收费与退换/退款规则、商品说明、护理与操作流程(SOP)、"
    "员工培训材料时，必须先用 kb_retrieve 检索本店内容库，基于店内真实资料作答，不要凭记忆或编造；\n"
    "2. 顾客问店内商品时可用 product_query 查询本店在售商品；\n"
    "3. 其他通用养宠知识可 tavily_search 联网。\n"
    "4. 当用户询问其他门店或与该店无关的宠物档案时，说明你只服务于本店并引导。\n"
    "回答使用中文，简洁专业；拿不准的明确提示「请以店内现行制度为准」。"
)


def _build_tools(kb_id: int | None, agent_mode: str = "public") -> list[dict]:
    """有可检索知识库时启用 kb_retrieve：店端用本店库，C 端用公共养护库。"""
    if kb_id is None:
        return TOOLS
    extra = STORE_KB_RETRIEVE_TOOL if agent_mode == "store" else PUBLIC_KB_RETRIEVE_TOOL
    return TOOLS + [extra]


def _merge_tool_delta(acc: dict[int, dict], tc: dict) -> None:
    idx = int(tc.get("index") or 0)
    slot = acc.setdefault(
        idx,
        {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
    )
    if tc.get("id"):
        slot["id"] = tc["id"]
    if tc.get("type"):
        slot["type"] = tc["type"]
    fn = tc.get("function") or {}
    if fn.get("name"):
        slot["function"]["name"] += fn["name"]
    if fn.get("arguments"):
        slot["function"]["arguments"] += fn["arguments"]


def _iter_deepseek(messages: list[dict], tools: list[dict]):
    """流式调用 DeepSeek。产出 delta 文本，最后产出 assistant_done。"""
    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": messages,
        "tools": tools,
        "temperature": 0.4,
        "stream": True,
    }
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    tool_acc: dict[int, dict] = {}
    content_parts: list[str] = []
    mode: str | None = None
    timeout = max(settings.DEEPSEEK_TIMEOUT, 120)
    with httpx.Client(timeout=timeout) as client:
        with client.stream(
            "POST",
            f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = (chunk.get("choices") or [{}])[0].get("delta") or {}
                except Exception:
                    continue
                tcs = delta.get("tool_calls")
                if tcs:
                    mode = "tools"
                    for tc in tcs:
                        _merge_tool_delta(tool_acc, tc)
                    continue
                piece = delta.get("content") or ""
                if piece and mode != "tools":
                    mode = "content"
                    content_parts.append(piece)
                    yield {"type": "delta", "content": piece}
    tool_calls = [tool_acc[i] for i in sorted(tool_acc)]
    msg: dict = {
        "role": "assistant",
        "content": "".join(content_parts) or None,
    }
    if tool_calls:
        msg["tool_calls"] = tool_calls
    yield {"type": "assistant_done", "message": msg}


def _tavily_search(query: str) -> str:
    key = settings.TAVILY_API_KEY
    if not key:
        return json.dumps({"error": "未配置 TAVILY_API_KEY，无法联网搜索"}, ensure_ascii=False)
    payload = {
        "api_key": key,
        "query": query,
        "max_results": settings.TAVILY_MAX_RESULTS,
        "include_answer": True,
        "search_depth": "basic",
    }
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post("https://api.tavily.com/search", json=payload)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        return json.dumps({"error": f"Tavily 调用失败: {e}"}, ensure_ascii=False)
    results = [
        {"title": x.get("title"), "url": x.get("url"), "content": x.get("content")}
        for x in data.get("results", [])
    ]
    return json.dumps(
        {"answer": data.get("answer"), "results": results},
        ensure_ascii=False,
    )


def _kb_retrieve(query: str, kb_id: int) -> str:
    try:
        hits = vector_db_service.search(query, kb_id)
    except Exception as e:
        return json.dumps(
            {"error": f"知识库检索服务暂不可用: {e}"}, ensure_ascii=False
        )
    return json.dumps(
        [{"text": h["text"], "score": round(h.get("score", 0), 4)} for h in hits],
        ensure_ascii=False,
    )


def _execute_tool(
    tool_name: str,
    args: dict,
    kb_id: int,
    user_id: int,
    loop=None,
    pet_id: int | None = None,
    store_id: int | None = None,
) -> str:
    if tool_name == "kb_retrieve":
        if not kb_id:
            return json.dumps({"error": "当前没有可检索的知识库"}, ensure_ascii=False)
        return _kb_retrieve(args.get("query", "") or "?", kb_id)
    if tool_name == "tavily_search":
        return _tavily_search(args.get("query", "") or "")
    if tool_name in (
        "pet_lookup",
        "vaccine_schedule",
        "product_query",
        "health_lookup",
        "match_resources",
        "create_lead",
    ):
        return _run_pet_tool(tool_name, args, user_id, loop, pet_id, store_id)
    return json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False)


def _run_pet_tool(
    tool_name: str,
    args: dict,
    user_id: int,
    loop=None,
    bound_pet_id: int | None = None,
    store_id: int | None = None,
) -> str:
    """同步桥接：宠物只读工具是 async 查询，必须调度回主事件循环执行，
    避免在线程里新建事件循环导致 Tortoise 连接池错乱。"""
    import asyncio

    from app.api.pets import lookup_health, lookup_pet, lookup_products, lookup_vaccines
    from app.models.models import User

    async def _impl():
        try:
            user = await User.get(id=user_id)
        except Exception:
            return {"error": "用户不存在"}
        if tool_name == "pet_lookup":
            return await lookup_pet(user, args.get("pet_id"), args.get("name"), bound_pet_id)
        if tool_name == "vaccine_schedule":
            return await lookup_vaccines(user, args.get("pet_id"), bound_pet_id)
        if tool_name == "product_query":
            return await lookup_products(
                user, args.get("pet_id"), args.get("category"), bound_pet_id, store_id
            )
        if tool_name == "health_lookup":
            return await lookup_health(user, args.get("pet_id"), bound_pet_id)
        if tool_name == "match_resources":
            from app.api.marketplace import match_resources

            return await match_resources(
                args.get("need_type"),
                args.get("species"),
                args.get("breed"),
                args.get("city"),
                args.get("budget"),
                args.get("keyword"),
            )
        if tool_name == "create_lead":
            from app.api.marketplace import create_lead_for_user

            return await create_lead_for_user(
                user,
                args.get("need_type") or "consult",
                args.get("summary") or "",
                args.get("city"),
                args.get("budget"),
            )
        return {"error": f"未知工具: {tool_name}"}

    if loop is not None and loop.is_running():
        result = asyncio.run_coroutine_threadsafe(_impl(), loop).result()
    else:
        # 无主循环可用时兜底：独立循环 + 独立 Tortoise 连接由 Tortoise 自动创建
        loop2 = asyncio.new_event_loop()
        try:
            result = loop2.run_until_complete(_impl())
        finally:
            loop2.close()
    return json.dumps(result, ensure_ascii=False)


def _tool_summary(tool_name: str, args: dict, agent_mode: str = "public") -> str:
    q = (args.get("query") or "").strip()
    if tool_name == "kb_retrieve":
        label = "本店内容库" if agent_mode == "store" else "养护知识库"
        return f"检索{label}：{q or '...'}"
    if tool_name == "tavily_search":
        return f"联网搜索：{q or '...'}"
    if tool_name == "pet_lookup":
        name = args.get("name") or args.get("pet_id") or "当前宠物"
        return f"查询宠物档案：{name}"
    if tool_name == "vaccine_schedule":
        return f"查询疫苗日程：宠物 {args.get('pet_id') or '当前'}"
    if tool_name == "product_query":
        pid = args.get("pet_id")
        cat = args.get("category")
        return f"查询商品：{('宠物 ' + str(pid)) if pid else (cat or '全部')}"
    if tool_name == "health_lookup":
        return f"查询体检与用药：宠物 {args.get('pet_id') or '当前'}"
    if tool_name == "match_resources":
        return f"匹配平台资源：{args.get('need_type') or '综合'}"
    if tool_name == "create_lead":
        return "登记运营线索"
    return f"调用工具：{tool_name}"


def run_agent(
    messages: list[dict],
    kb_id: int | None,
    user_id: int | None = None,
    loop=None,
    pet_id: int | None = None,
    store_id: int | None = None,
    agent_mode: str = "public",
):
    """智能体工具循环（生成器）。

    参数 messages: 已含 system + 历史 + 当前用户提问的完整消息列表。
    产出事件: {"type": "tool", name, args, summary} | {"type": "delta", content}
    """
    msgs = [dict(m) for m in messages]
    tools = _build_tools(kb_id, agent_mode)
    names = TOOL_NAMES | ({"kb_retrieve"} if kb_id else set())
    iters = 0
    while iters < settings.AGENT_MAX_ITERS:
        iters += 1
        model_msg: dict = {}
        streamed = False
        for ev in _iter_deepseek(msgs, tools):
            if ev["type"] == "delta":
                streamed = True
                yield {"type": "delta", "content": ev["content"]}
            elif ev["type"] == "assistant_done":
                model_msg = ev["message"]

        tool_calls = model_msg.get("tool_calls")
        if tool_calls:
            msgs.append(
                {k: v for k, v in model_msg.items() if k != "tool_calls" and v is not None}
                | {"tool_calls": tool_calls}
            )
            for tc in tool_calls:
                fn = tc.get("function", {})
                tool_name = fn.get("name", "")
                args: dict = {}
                if tool_name not in names:
                    result = json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False)
                else:
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = _execute_tool(
                        tool_name, args, kb_id or 0, user_id or 0, loop, pet_id, store_id
                    )
                yield {
                    "type": "tool",
                    "name": tool_name,
                    "args": args,
                    "summary": _tool_summary(tool_name, args, agent_mode),
                }
                msgs.append({"role": "tool", "tool_call_id": tc.get("id"), "content": result})
            continue

        if not streamed:
            content = (model_msg.get("content") or "").strip()
            yield {
                "type": "delta",
                "content": content or "（模型未生成内容，请换个问法重试）",
            }
        return

    yield {"type": "delta", "content": "（已达工具调用轮次上限，请简化问题或换个问法）"}


def run_agent_last(
    messages: list[dict],
    kb_id: int | None,
    user_id: int | None = None,
    loop=None,
    pet_id: int | None = None,
    store_id: int | None = None,
    agent_mode: str = "public",
) -> str:
    """非流式便捷入口: 执行完整工具循环，返回最终文本回答。"""
    last = ""
    for ev in run_agent(messages, kb_id, user_id, loop, pet_id, store_id, agent_mode):
        if ev["type"] == "delta":
            last += ev["content"]
    return last