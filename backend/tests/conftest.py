"""可重复的 API 测试夹具。

默认使用一次性 SQLite 文件，不读取开发者的 MySQL ``DATABASE_URL``，
因此本机和 CI 都不需要 MySQL / Milvus。
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# 必须在导入 app 之前固定数据库，避免命中本机 MySQL 或 .env。
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND_ROOT / ".pytest.sqlite3"
for _suffix in ("", "-journal", "-wal", "-shm"):
    _stale = Path(str(_DB_PATH) + _suffix) if _suffix else _DB_PATH
    if _stale.exists():
        _stale.unlink()

# 三个斜杠表示绝对路径：sqlite:///tmp/foo.db
os.environ["DATABASE_URL"] = f"sqlite://{_DB_PATH.as_posix()}"
os.environ.setdefault("SECRET_KEY", "pytest-secret")
# 即便某条路径误触发向量化，也不要去拉本地 bge-m3。
os.environ.setdefault("EMBEDDING_PROVIDER", "api")
os.environ.setdefault("EMBEDDING_API_URL", "http://127.0.0.1:9")
os.environ.setdefault("DEEPSEEK_API_KEY", "")

PASSWORD = "Passw0rd!a"


def uniq(prefix: str) -> str:
    """生成合法用户名：字母开头，3-24 位。"""
    name = f"{prefix}{uuid.uuid4().hex[:8]}"
    return name[:24]


@pytest.fixture(scope="session")
def client():
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def admin_token(client: TestClient) -> str:
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register(client: TestClient, username: str, role: str = "user") -> dict:
    resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": PASSWORD,
            "email": f"{username}@t.com",
            "role": role,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def login(client: TestClient, username: str, password: str = PASSWORD) -> str:
    resp = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def create_store(client: TestClient, admin_token: str, name: str, store_type: str = "shop") -> dict:
    resp = client.post(
        "/api/stores",
        headers=auth(admin_token),
        json={"name": name, "store_type": store_type, "city": "上海"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def assign_staff(
    client: TestClient,
    admin_token: str,
    store_id: int,
    user_id: int,
    staff_role: str,
) -> None:
    resp = client.post(
        f"/api/stores/{store_id}/staff",
        headers=auth(admin_token),
        json={"user_id": user_id, "staff_role": staff_role},
    )
    assert resp.status_code == 200, resp.text
