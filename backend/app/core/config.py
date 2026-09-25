from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ---- 应用 ----
    APP_NAME: str = "宠智联"
    SECRET_KEY: str = "change-me-in-prod"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 天，减少频繁过期

    # ---- 关系数据库 (MySQL) ----
    DATABASE_URL: str = "mysql://root:123456@127.0.0.1:3306/ai_kb"

    # ---- 向量数据库 (Milvus) ----
    MILVUS_HOST: str = "192.168.133.131"
    MILVUS_PORT: str = "19530"
    MILVUS_COLLECTION: str = "knowledge_collection"
    EMBEDDING_DIM: int = 1024  # bge-m3 dense 向量的维度

    # ---- Embedding 模型 ----
    # provider: local(本地 sentence-transformers) | api(任意 OpenAI 兼容 /v1/embeddings)
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_API_URL: str = ""
    EMBEDDING_API_KEY: str = ""

    # ---- LLM (DeepSeek) ----
    DEEPSEEK_API_KEY: str = "sk-312dc8d047fa46f9b4daf4d510763668"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_TIMEOUT: int = 60

    # ---- Tavily 联网搜索 ----
    TAVILY_API_KEY: str = ""
    TAVILY_MAX_RESULTS: int = 5
    # 智能体工具调用最大轮次（防死循环）
    AGENT_MAX_ITERS: int = 6

    # ---- 超管 ----
    # 指定用户名作为唯一超管；该用户登录后可管理公共知识库并查看所有数据
    SUPER_ADMIN_USERNAME: str = "admin"
    # 公共知识库名称，系统启动时自动创建（所有人可见、Admin 专属管理）
    PUBLIC_KB_NAME: str = "公共知识库"

    # ---- 文档解析 ----
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 5
    UPLOAD_DIR: str = "uploads"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()