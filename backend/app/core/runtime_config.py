"""运行时配置：生产默认失败关闭，演示模式必须显式打开。"""
from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.security import check_password_strength

# 只在演示模式作为 JWT 签名密钥。生产校验会拒绝它。
DEMO_JWT_SECRET = "demo-only-not-for-production-do-not-use"
# 本地 docker / 开发库的历史口令。生产环境拒绝这段连接串。
DEMO_DATABASE_URL = "mysql://root:123456@127.0.0.1:3306/ai_kb"
KNOWN_DEMO_PASSWORDS = frozenset({"admin123", "Passw0rd!a"})
INSECURE_SECRET_KEYS = frozenset(
    {
        "",
        "change-me",
        "change-me-in-prod",
        "changeme",
        "secret",
        "demo",
        DEMO_JWT_SECRET,
    }
)
DEFAULT_LOCAL_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)

_prepared = False


def reset_runtime_state() -> None:
    """测试用：清空配置缓存与一次性准备标记。"""
    global _prepared
    _prepared = False
    get_settings.cache_clear()


def is_demo_mode(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if settings.DEMO_MODE:
        return True
    return (settings.APP_ENV or "").strip().lower() in {"demo", "dev", "development"}


def secret_is_unsafe(secret: str | None) -> bool:
    key = (secret or "").strip()
    if key in INSECURE_SECRET_KEYS:
        return True
    return len(key) < 32


def is_demo_database_url(url: str | None) -> bool:
    raw = (url or "").strip()
    if not raw:
        return False
    if raw in {
        DEMO_DATABASE_URL,
        "mysql://root:123456@localhost:3306/ai_kb",
        "mysql://root:123456@mysql:3306/ai_kb",
    }:
        return True
    # 任意主机上的 root/123456 都视为演示口令
    return "://root:123456@" in raw


def apply_runtime_defaults(settings: Settings) -> None:
    """演示模式补齐本地默认值。生产模式不填入任何演示密钥。"""
    if not is_demo_mode(settings):
        return
    if secret_is_unsafe(settings.SECRET_KEY):
        settings.SECRET_KEY = DEMO_JWT_SECRET
    if not (settings.DATABASE_URL or "").strip():
        settings.DATABASE_URL = DEMO_DATABASE_URL


def resolve_cors_origins(settings: Settings) -> list[str]:
    raw = (settings.CORS_ORIGINS or "").strip()
    if raw == "*":
        raise RuntimeError("CORS_ORIGINS 不允许为 *，请配置逗号分隔的来源白名单")
    origins: list[str] = []
    for part in raw.split(","):
        item = part.strip().rstrip("/")
        if not item:
            continue
        if item == "*":
            raise RuntimeError("CORS_ORIGINS 不允许包含 *")
        origins.append(item)
    if origins:
        return origins
    if is_demo_mode(settings):
        return list(DEFAULT_LOCAL_ORIGINS)
    raise RuntimeError("生产环境必须设置 CORS_ORIGINS（不能为空，也不能为 *）")


def ensure_media_backend_supported(settings: Settings) -> None:
    kind = (settings.MEDIA_STORAGE or "db").strip().lower()
    if kind in {"db", "filesystem"}:
        return
    if kind == "s3":
        missing = [
            name
            for name, value in (
                ("S3_ENDPOINT", settings.S3_ENDPOINT),
                ("S3_BUCKET", settings.S3_BUCKET),
                ("S3_ACCESS_KEY", settings.S3_ACCESS_KEY),
                ("S3_SECRET_KEY", settings.S3_SECRET_KEY),
            )
            if not (value or "").strip()
        ]
        missing_text = f"（缺少 {', '.join(missing)}）" if missing else ""
        raise RuntimeError(
            "MEDIA_STORAGE=s3 尚未提供可写实现，已拒绝启动，避免数据写到半成品客户端。"
            f"{missing_text} 请继续使用 db（默认，兼容 Base64）或 filesystem。"
            "对象存储迁移步骤见文档。"
        )
    raise RuntimeError("MEDIA_STORAGE 只能是 db、filesystem 或 s3")


def assert_production_admin_password(password: str) -> None:
    """生产环境创建超管时调用。已知演示口令即使满足强度规则也拒绝。"""
    secret = (password or "").strip()
    if not secret or secret in KNOWN_DEMO_PASSWORDS:
        raise RuntimeError(
            "生产环境不存在超管，且未提供可用的 SUPER_ADMIN_PASSWORD。拒绝使用演示口令创建账号。"
        )
    strength_error = check_password_strength(secret)
    if strength_error:
        raise RuntimeError(f"SUPER_ADMIN_PASSWORD 不符合强度要求：{strength_error}")


def demo_user_password(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if not is_demo_mode(settings):
        raise RuntimeError("生产环境禁止读取演示用户口令")
    return (settings.DEMO_PASSWORD or "").strip() or "Passw0rd!a"


def demo_admin_password(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if not is_demo_mode(settings):
        raise RuntimeError("生产环境禁止读取演示超管口令")
    return (settings.DEMO_ADMIN_PASSWORD or "").strip() or "admin123"


def validate_runtime_config(settings: Settings) -> None:
    ensure_media_backend_supported(settings)
    resolve_cors_origins(settings)
    if is_demo_mode(settings):
        if not (settings.DATABASE_URL or "").strip():
            raise RuntimeError("演示模式缺少 DATABASE_URL")
        if not (settings.SECRET_KEY or "").strip():
            raise RuntimeError("演示模式缺少 SECRET_KEY")
        return

    errors: list[str] = []
    if secret_is_unsafe(settings.SECRET_KEY):
        errors.append("SECRET_KEY 必须由环境变量提供，至少 32 位，且不能使用演示占位符")
    database_url = (settings.DATABASE_URL or "").strip()
    if not database_url:
        errors.append("DATABASE_URL 必须由环境变量提供")
    elif is_demo_database_url(database_url):
        errors.append("DATABASE_URL 仍是演示库口令（root/123456），生产环境请更换数据库账号与密码")
    if errors:
        raise RuntimeError(
            "生产配置拒绝启动（APP_ENV 默认为 production）。"
            "本地演示请设置 APP_ENV=demo 后重启；生产环境请注入独立密钥："
            + "；".join(errors)
        )


def prepare_runtime() -> tuple[Settings, list[str]]:
    """导入应用或 Aerich 时调用一次：演示模式补默认值，生产模式失败关闭。"""
    global _prepared
    settings = get_settings()
    if not _prepared:
        apply_runtime_defaults(settings)
        validate_runtime_config(settings)
        _prepared = True
    return settings, resolve_cors_origins(settings)


def build_tortoise_config(database_url: str) -> dict:
    return {
        "connections": {"default": database_url},
        "apps": {
            "models": {
                "models": ["app.models.models", "aerich.models"],
                "default_connection": "default",
            }
        },
    }
