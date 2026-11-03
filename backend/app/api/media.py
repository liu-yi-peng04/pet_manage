"""图片上传与读取。

默认仍把字节存进 MySQL。GET 必须带登录态：Authorization 头，或 access_token 查询参数
（<img> 无法自定义请求头）。私有图片还要过属主校验；目录类图片对已登录用户可见。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.api.auth import authenticate_token, get_current_user, oauth2_scheme_optional
from app.models.models import MediaAsset, User
from app.schemas.schemas import MediaOut
from app.services.media_access import can_read_media
from app.services.media_storage import get_media_storage

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

    storage = get_media_storage()
    asset = await MediaAsset.create(
        owner=user,
        purpose=purpose,
        filename=file.filename or f"upload{ALLOWED_TYPES[content_type]}",
        content_type=content_type,
        size=len(raw),
        data_b64="",
    )
    try:
        stored = await storage.put(
            asset_id=asset.id,
            filename=asset.filename,
            content_type=content_type,
            data=raw,
        )
        asset.data_b64 = stored
        await asset.save(update_fields=["data_b64"])
    except Exception:
        await asset.delete()
        raise

    return MediaOut(
        id=asset.id,
        url=f"/api/media/{asset.id}",
        filename=asset.filename,
        content_type=asset.content_type,
        size=asset.size,
        purpose=asset.purpose,
    )


@router.get("/{media_id}")
async def get_media(
    media_id: int,
    access_token: str | None = Query(
        default=None,
        description="浏览器 img 不能带 Authorization 头时，传与登录相同的 JWT",
    ),
    header_token: str | None = Depends(oauth2_scheme_optional),
):
    user = await authenticate_token(header_token or access_token)
    asset = await MediaAsset.get_or_none(id=media_id)
    if not asset:
        raise HTTPException(status_code=404, detail="图片不存在")
    if not can_read_media(user, asset):
        raise HTTPException(status_code=403, detail="无权查看该图片")
    try:
        data = await get_media_storage().read(asset.data_b64)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="图片数据损坏或文件缺失") from exc
    if not data:
        raise HTTPException(status_code=500, detail="图片数据损坏或文件缺失")
    return Response(
        content=data,
        media_type=asset.content_type or "image/jpeg",
        headers={
            "Cache-Control": "private, max-age=86400",
            "X-Content-Type-Options": "nosniff",
        },
    )
