"""图片上传：Base64 写入 MySQL，公开读取供 <img> 使用。"""
from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.api.auth import get_current_user
from app.models.models import MediaAsset, User
from app.schemas.schemas import MediaOut

router = APIRouter(prefix="/api/media", tags=["media"])

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_BYTES = 5 * 1024 * 1024  # 5MB
PURPOSES = {"pet", "listing", "product", "trainer", "other"}


@router.post("/upload", response_model=MediaOut)
async def upload_media(
    file: UploadFile = File(...),
    purpose: str = Query("other"),
    user: User = Depends(get_current_user),
):
    purpose = (purpose or "other").strip().lower()
    if purpose not in PURPOSES:
        raise HTTPException(status_code=400, detail=f"未知用途: {purpose}")

    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_TYPES:
        name = (file.filename or "").lower()
        if name.endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        elif name.endswith(".png"):
            content_type = "image/png"
        elif name.endswith(".webp"):
            content_type = "image/webp"
        elif name.endswith(".gif"):
            content_type = "image/gif"
        else:
            raise HTTPException(status_code=400, detail="仅支持 jpg/png/webp/gif 图片")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="空文件")
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="图片不能超过 5MB")

    asset = await MediaAsset.create(
        owner=user,
        purpose=purpose,
        filename=file.filename or f"upload{ALLOWED_TYPES[content_type]}",
        content_type=content_type,
        size=len(raw),
        data_b64=base64.b64encode(raw).decode("ascii"),
    )
    return MediaOut(
        id=asset.id,
        url=f"/api/media/{asset.id}",
        filename=asset.filename,
        content_type=asset.content_type,
        size=asset.size,
        purpose=asset.purpose,
    )


@router.get("/{media_id}")
async def get_media(media_id: int):
    """公开读取：便于卡片 <img src> 直接引用，无需带 token。"""
    asset = await MediaAsset.get_or_none(id=media_id)
    if not asset:
        raise HTTPException(status_code=404, detail="图片不存在")
    try:
        data = base64.b64decode(asset.data_b64)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"图片数据损坏: {e}")
    return Response(
        content=data,
        media_type=asset.content_type or "image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
