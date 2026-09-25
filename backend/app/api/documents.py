import shutil
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
)
from starlette.concurrency import run_in_threadpool
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.api.auth import get_current_user
from app.api.knowledge_base import find_kb
from app.core.config import get_settings
from app.models.models import Document, KnowledgeBase, User
from app.schemas.schemas import DocumentOut
from app.services.document_service import extract_text, split_into_chunks
from app.services.vectordb_service import vector_db_service

router = APIRouter(prefix="/api/kb/{kb_id}/documents", tags=["documents"])
settings = get_settings()

# backend 根目录（本项目 = app/api/documents.py 的上三级），uploads 基于它解析为绝对路径
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_ROOT = Path(settings.UPLOAD_DIR)
if not UPLOAD_ROOT.is_absolute():
    UPLOAD_ROOT = BACKEND_DIR / UPLOAD_ROOT

ALLOWED_TYPES = {"pdf", "docx", "txt", "md", "markdown", "mdx", "csv"}


async def _can_manage_docs(kb: KnowledgeBase, user: User) -> bool:
    """是否可以往该知识库上传/删除文档：
    - 门店内容库：仅超管或本店 staff
    - 本人私有库：可以
    - 公共库：仅 admin 可以
    """
    if kb.store_id is not None:
        return user.role == "admin" or (
            user.role == "staff" and user.store_id == kb.store_id
        )
    if kb.is_public:
        return user.role == "admin"
    return kb.owner_id == user.id


@router.post("", response_model=DocumentOut)
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    kb = await find_kb(kb_id, user)
    if not await _can_manage_docs(kb, user):
        raise HTTPException(status_code=403, detail="公共知识库仅管理员可上传文档")

    file_type = (file.filename or "").split(".")[-1].lower()
    if file_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_type}")

    upload_root = UPLOAD_ROOT / str(kb.id)
    upload_root.mkdir(parents=True, exist_ok=True)
    save_path = upload_root / f"{file.filename or 'upload'}"
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    async with in_transaction():
        doc = await Document.create(
            kb=kb,
            filename=file.filename or "upload",
            file_path=str(save_path),
            file_type=file_type,
            status="indexing",
        )
        try:
            # embedding/入库是耗时同步调用，放线程池避免阻塞事件循环
            def _index():
                text = extract_text(str(save_path), file_type)
                chunks = split_into_chunks(text)
                vector_db_service.add_document_chunks(doc.id, kb.id, chunks)

            await run_in_threadpool(_index)
            doc.status = "indexed"
            await doc.save()
        except Exception as e:
            doc.status = "failed"
            await doc.save()
            raise HTTPException(status_code=500, detail=f"解析入库失败: {e}")

    return doc


@router.get("", response_model=list[DocumentOut])
async def list_documents(kb_id: int, user: User = Depends(get_current_user)):
    kb = await find_kb(kb_id, user)
    return await Document.filter(kb=kb).order_by("-id")


# ---------------------------------------------------------------------------
# 独立文档路由（资源级权限：文档归属跟随其知识库）
# ---------------------------------------------------------------------------
doc_router_indep = APIRouter(prefix="/api/documents", tags=["documents"])


async def _get_document_for_manage(doc_id: int, user: User) -> Document:
    from tortoise.exceptions import DoesNotExist

    try:
        doc = await Document.get(id=doc_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="文档不存在")
    kb = await KnowledgeBase.get_or_none(id=doc.kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="文档不存在")
    # 门店内容库：仅超管或本店 staff 可删
    if kb.store_id is not None:
        if user.role == "admin" or (
            user.role == "staff" and user.store_id == kb.store_id
        ):
            return doc
        raise HTTPException(status_code=403, detail="无权删除该文档")
    # 删除权限：本人私有库文档，或 public 库且 admin
    if kb.owner_id == user.id and not kb.is_public:
        return doc
    if kb.is_public and user.role == "admin":
        return doc
    raise HTTPException(status_code=403, detail="无权删除该文档")


@doc_router_indep.get("", response_model=list[DocumentOut])
async def list_all_documents(user: User = Depends(get_current_user)):
    """列出当前用户可访问的所有知识库下的文档（含公共库）。"""
    # 可访问知识库：admin 全部；普通用户自己的 + public
    if user.role == "admin":
        kbs = await KnowledgeBase.all()
    else:
        kbs = await KnowledgeBase.filter(Q(owner=user) | Q(is_public=True))
    kb_ids = [k.id for k in kbs]
    if not kb_ids:
        return []
    return await Document.filter(kb_id__in=kb_ids).order_by("-id")


@doc_router_indep.delete("/{doc_id}")
async def delete_document(doc_id: int, user: User = Depends(get_current_user)):
    doc = await _get_document_for_manage(doc_id, user)
    # 删除 Milvus 中该文档的向量（可选，容错）
    try:
        vector_db_service.delete_by_doc(doc.id)
    except Exception:
        pass
    # 物理删除文件
    try:
        p = Path(doc.file_path)
        if p.exists():
            p.unlink()
    except OSError:
        pass
    await doc.delete()
    return {"detail": "已删除"}