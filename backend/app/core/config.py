from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ---- 应用 ----
    APP_NAME: str = "宠智联"
    # production（默认）失败关闭；演示闭环必须显式 APP_ENV=demo 或 DEMO_MODE=true
    APP_ENV: str = "production"
    DEMO_MODE: bool = False
    # 仅演示模式生效：启动时 generate_schemas + 旧库缺列补丁。生产环境忽略此项。
    DEMO_AUTO_SCHEMA: bool = True
    # 生产环境必须由环境变量注入，且不能是占位符。演示模式可留空，由运行时填入仅供本地的密钥。
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 天，减少频繁过期

    # ---- 关系数据库 (MySQL) ----
    # 不设带口令的默认值。演示模式留空时才回落到本地演示库。
    DATABASE_URL: str = ""

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
    # 不得把真实密钥写进源码。未配置时登录与媒体仍可用，对话接口会在调用时失败。
    DEEPSEEK_API_KEY: str = ""
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
    # 仅生产环境、且库中还没有超管时使用。禁止 admin123 等演示口令。
    SUPER_ADMIN_PASSWORD: str = ""
    # 仅 APP_ENV=demo / DEMO_MODE 时生效；留空则使用文档中的演示口令。
    DEMO_PASSWORD: str = ""
    DEMO_ADMIN_PASSWORD: str = ""
    # 公共知识库名称，系统启动时自动创建（所有人可见、Admin 专属管理）
    PUBLIC_KB_NAME: str = "公共知识库"

    # ---- 跨域 ----
    # 逗号分隔的来源白名单。禁止 *。默认只放行本地 Vite。
    CORS_ORIGINS: str = "http://127.0.0.1:5173,http://localhost:5173"

    # ---- 媒体存储 ----
    # db：Base64 存 MySQL（默认，演示闭环不变）
    # filesystem：新文件落盘，读取仍兼容库内 Base64
    # s3：仅预留，当前版本拒绝启动，避免半成品客户端误写
    MEDIA_STORAGE: str = "db"
    MEDIA_FS_ROOT: str = "uploads/media"
    S3_ENDPOINT: str = ""
    S3_BUCKET: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "us-east-1"

    # ---- 文档解析 ----
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 5
    UPLOAD_DIR: str = "uploads"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
