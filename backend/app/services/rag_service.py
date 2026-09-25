from app.services.llm_service import chat, chat_stream
from app.services.vectordb_service import vector_db_service


def retrieve(query: str, kb_id: int) -> list[dict]:
    """检索相关文档块并构造 system 上下文消息。"""
    hits = vector_db_service.search(query, kb_id)
    context = "\n\n".join(f"[片段 {i+1}] {h['text']}" for i, h in enumerate(hits))
    system_prompt = (
        "你是一个企业技术知识库助手。请严格围绕下面提供的资料回答问题；"
        "如果资料中没有相关内容，请明确说'资料库中没有相关信息'，不要编造。\n\n"
        f"资料:\n{context}"
    )
    return [{"role": "system", "content": system_prompt}]


def build_messages(query: str, kb_id: int, history: list[dict] | None = None) -> list[dict]:
    messages = retrieve(query, kb_id)
    messages.extend(history or [])
    messages.append({"role": "user", "content": query})
    return messages


def ask(query: str, kb_id: int, history: list[dict] | None = None) -> str:
    """RAG 主流程: 检索相关文档块 -> 拼进上下文 -> 交给 DeepSeek 生成回答。"""
    messages = build_messages(query, kb_id, history)
    return chat(messages)


def ask_stream(query: str, kb_id: int, history: list[dict] | None = None):
    """流式 RAG: 检索上下文拼好后，以 SSE 逐段产出回答增量。"""
    messages = build_messages(query, kb_id, history)
    yield from chat_stream(messages)


def ask_stream_with_messages(messages: list[dict]):
    """直接对已组装好的 messages 做流式生成（用于会话已准备好的场景）。"""
    yield from chat_stream(messages)