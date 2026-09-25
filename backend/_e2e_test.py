import io, random
import httpx

base = "http://127.0.0.1:8000"
c = httpx.Client(base_url=base, timeout=60)

# 1 注册 2 登录
un = f"e2e_{random.randint(1000,99999)}"
r = c.post("/api/auth/register", json={"username": un, "password": "pass123"})
print("[注册]", r.status_code, un)
r = c.post("/api/auth/login", json={"username": un, "password": "pass123"})
token = r.json()["access_token"]
print("[登录]", r.status_code, "token长度", len(token))
H = {"Authorization": f"Bearer {token}"}

# 3 建库
r = c.post("/api/kb", json={"name": "techkb", "description": "test"}, headers=H)
kb_id = r.json()["id"]
print("[建库]", r.status_code, "id", kb_id)

# 4 上传文档
doc_text = (
    "Milvus is an open-source vector database for storing and retrieving high-dimensional vectors. "
    "RAG retrieval-augmented generation first retrieves relevant chunks from a knowledge base "
    "then feeds them to an LLM to generate answers. FastAPI is a high-performance Python web "
    "framework based on type hints."
)
r = c.post(f"/api/kb/{kb_id}/documents", headers=H,
           files={"file": ("test.txt", io.BytesIO(doc_text.encode("utf-8")), "text/plain")})
print("[上传文档]", r.status_code)
print("  响应体:", repr(r.text[:300]))
try:
    print("  json:", r.json())
except Exception as e:
    print("  json解析失败:", e)

# 5 问答
r = c.post("/api/chat", headers=H, json={"content": "什么是RAG？", "kb_id": kb_id})
print("[问答]", r.status_code)
if r.status_code == 200:
    j = r.json()
    print("  回答:", j.get("content", "")[:300])
else:
    print("  错误:", r.text[:300])