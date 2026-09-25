from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q

from app.api.auth import get_current_user
from app.core.config import get_settings
from app.models.models import ChatMessage, Conversation, Document, KnowledgeBase, User
from app.schemas.schemas import KnowledgeBaseCreate, KnowledgeBaseOut
from app.services.vectordb_service import vector_db_service

router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])


def is_admin(user: User) -> bool:
    return user.role == "admin"


async def require_admin(user: User) -> User:
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


async def accessible_kbs(user: User):
    """查询当前用户可访问的知识库：超管全部；普通用户自己的+公开库；
    staff 额外含本店内容库。"""
    _order = {"-is_public", "-id"}
    if is_admin(user):
        return await KnowledgeBase.all().order_by("-is_public", "-id")
    if user.role == "staff" and user.store_id is not None:
        return await KnowledgeBase.filter(
            Q(owner=user) | Q(is_public=True) | Q(store_id=user.store_id)
        ).order_by("-is_public", "-id")
    return await KnowledgeBase.filter(
        Q(owner=user) | Q(is_public=True)
    ).order_by("-is_public", "-id")


async def find_kb(kb_id: int, user: User) -> KnowledgeBase:
    """返回当前用户可读取的知识库；不存在 404，越权 403。
    支持门店内容库：本店 staff 可读本店库，admin 可读全部。"""
    try:
        kb = await KnowledgeBase.get(id=kb_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if is_admin(user):
        return kb
    # 门店内容库：仅本店 staff（或超管）可读，店间隔离
    if kb.store_id is not None:
        if user.role == "staff" and user.store_id == kb.store_id:
            return kb
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    if kb.is_public or kb.owner_id == user.id:
        return kb
    raise HTTPException(status_code=403, detail="无权访问该知识库")


async def find_owned_kb(kb_id: int, user: User) -> KnowledgeBase:
    """返回当前用户可管理其知识库本体的库：
    超管可管理一切；普通用户仅可管理自己非公开、非门店的私有库；
    公开库与门店内容库的知识库本体仅 admin 可删（文档级权限在 documents.py 另行校验）。"""
    try:
        kb = await KnowledgeBase.get(id=kb_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if is_admin(user):
        return kb
    if kb.owner_id != user.id or kb.is_public or kb.store_id is not None:
        raise HTTPException(status_code=403, detail="无权管理该知识库")
    return kb


@router.post("", response_model=KnowledgeBaseOut)
async def create_kb(data: KnowledgeBaseCreate, user: User = Depends(get_current_user)):
    kb = await KnowledgeBase.create(
        name=data.name, description=data.description, owner=user
    )
    return kb


@router.get("", response_model=list[KnowledgeBaseOut])
async def list_kb(user: User = Depends(get_current_user)):
    return await accessible_kbs(user)


@router.delete("/{kb_id}")
async def delete_kb(kb_id: int, user: User = Depends(get_current_user)):
    kb = await find_owned_kb(kb_id, user)

    # 1. 清理 Milvus 中的向量
    try:
        vector_db_service.delete_by_kb(kb_id)
    except Exception:
        pass  # 向量缺失不阻断删除

    # 2. 清理数据库关联记录
    conv_ids = await Conversation.filter(kb_id=kb_id).values_list("id", flat=True)
    if conv_ids:
        await ChatMessage.filter(conversation_id__in=conv_ids).delete()
        await Conversation.filter(id__in=conv_ids).delete()
    await Document.filter(kb=kb).delete()

    # 3. 物理删除本地上传目录
    settings = get_settings()
    BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
    upload_root = Path(settings.UPLOAD_DIR)
    if not upload_root.is_absolute():
        upload_root = BACKEND_DIR / upload_root
    kb_dir = upload_root / str(kb_id)
    if kb_dir.exists():
        import shutil

        try:
            shutil.rmtree(kb_dir)
        except OSError:
            pass  # 目录删除失败不阻断

    # 4. 删除知识库本身
    await kb.delete()
    return {"detail": "已删除"}