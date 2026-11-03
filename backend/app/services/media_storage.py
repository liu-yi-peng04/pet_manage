"""媒体存储抽象。

默认 db：继续把 Base64 放进 MySQL，演示闭环不变。
filesystem：新上传写到本地目录，列里只存指针；读取时仍认历史 Base64。
s3：配置位已留出，但本版本拒绝启用，避免半成品上传把数据写丢。
"""
from __future__ import annotations

import base64
from pathlib import Path

from app.core.config import Settings, get_settings

POINTER_PREFIX = "storage:"
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def parse_storage_pointer(stored: str) -> tuple[str, str] | None:
    if not stored or not stored.startswith(POINTER_PREFIX):
        return None
    rest = stored[len(POINTER_PREFIX) :]
    backend, sep, key = rest.partition(":")
    if not sep or not backend or not key:
        return None
    return backend, key


def _safe_file(root: Path, key: str) -> Path:
    # 指针只应由本服务生成。解析后必须仍落在根目录内。
    root_resolved = root.resolve()
    path = (root_resolved / key).resolve()
    if path != root_resolved and root_resolved not in path.parents:
        raise ValueError("非法媒体路径")
    return path


def read_stored_bytes(stored: str, fs_root: Path) -> bytes:
    parsed = parse_storage_pointer(stored or "")
    if parsed is None:
        try:
            return base64.b64decode(stored or "", validate=False)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("图片 Base64 无法解码") from exc
    backend, key = parsed
    if backend == "filesystem":
        path = _safe_file(fs_root, key)
        if not path.is_file():
            raise FileNotFoundError("图片文件不存在")
        return path.read_bytes()
    if backend == "db":
        return base64.b64decode(key, validate=False)
    raise ValueError(f"暂不支持的媒体存储后端: {backend}")


class DatabaseMediaStorage:
    name = "db"

    def __init__(self, fs_root: Path):
        self.fs_root = fs_root

    async def put(self, *, asset_id: int, filename: str, content_type: str, data: bytes) -> str:
        del asset_id, filename, content_type
        return base64.b64encode(data).decode("ascii")

    async def read(self, stored: str) -> bytes:
        # 即使当前是 db，也要能读以前写成文件系统指针的对象。
        return read_stored_bytes(stored, self.fs_root)


class FilesystemMediaStorage:
    name = "filesystem"

    def __init__(self, fs_root: Path):
        self.fs_root = fs_root

    async def put(self, *, asset_id: int, filename: str, content_type: str, data: bytes) -> str:
        del content_type
        suffix = Path(filename or "").suffix.lower()
        if suffix not in _IMAGE_SUFFIXES:
            suffix = ".bin"
        relative = f"{asset_id}{suffix}"
        self.fs_root.mkdir(parents=True, exist_ok=True)
        path = _safe_file(self.fs_root, relative)
        path.write_bytes(data)
        return f"{POINTER_PREFIX}filesystem:{relative}"

    async def read(self, stored: str) -> bytes:
        return read_stored_bytes(stored, self.fs_root)


def get_media_storage(settings: Settings | None = None):
    settings = settings or get_settings()
    kind = (settings.MEDIA_STORAGE or "db").strip().lower()
    root = Path(settings.MEDIA_FS_ROOT)
    if kind == "filesystem":
        return FilesystemMediaStorage(root)
    if kind == "db":
        return DatabaseMediaStorage(root)
    if kind == "s3":
        raise RuntimeError(
            "MEDIA_STORAGE=s3 尚未实现写入。请使用 db 或 filesystem，对象存储迁移见文档。"
        )
    raise RuntimeError("MEDIA_STORAGE 只能是 db、filesystem 或 s3")
