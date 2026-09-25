import json

import httpx

from app.core.config import get_settings

settings = get_settings()


def chat(messages: list[dict], temperature: float = 0.7) -> str:
    """调用 DeepSeek 对话接口，messages 形如 [{"role":"user","content":...}]。"""
    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=settings.DEEPSEEK_TIMEOUT) as client:
        resp = client.post(
            f"{settings.DEEPSEEK_BASE_URL}/chat/completions", json=payload, headers=headers
        )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def chat_stream(messages: list[dict], temperature: float = 0.7):
    """以 SSE 方式流式调用 DeepSeek，逐段产出文本增量（generator）。

    语义与 chat() 一致，返回的是迭代器，产出形如 {"type": DONE|delta|error} 的事件。
    """
    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=settings.DEEPSEEK_TIMEOUT) as client:
            with client.stream(
                "POST",
                f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
            ) as resp:
                if resp.status_code != 200:
                    yield {"type": "error", "content": f"大模型返回 {resp.status_code}"}
                    return
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                    except Exception:
                        delta = ""
                    if delta:
                        yield {"type": "delta", "content": delta}
        yield {"type": "done", "content": ""}
    except httpx.HTTPError as e:
        yield {"type": "error", "content": f"调用失败: {e}"}