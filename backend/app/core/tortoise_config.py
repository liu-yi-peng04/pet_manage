"""Aerich 与应用启动共用的 Tortoise 配置。"""
from app.core.runtime_config import build_tortoise_config, prepare_runtime

_settings, _cors_origins = prepare_runtime()
TORTOISE_ORM = build_tortoise_config(_settings.DATABASE_URL)
CORS_ORIGINS = _cors_origins
