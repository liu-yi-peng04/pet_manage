from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from tortoise.exceptions import DoesNotExist

from app.api.auth import get_current_user
from app.api.knowledge_base import is_admin
from app.models.models import Product, Store, User
from app.schemas.schemas import (
    ProductIn,
    ProductOut,
    StaffAssignIn,
    StaffOut,
    StoreIn,
    StoreOut,
)

router = APIRouter(prefix="/api/stores", tags=["stores"])

PRODUCT_CATEGORIES = {"cage", "toy", "supply", "food", "health"}
STAFF_ROLES = {"manager", "assistant"}


def to_product_out(p: Product) -> ProductOut:
    """商品序列化：附带门店名称/电话/地址，便于 C 端导流到店。"""
    s = getattr(p, "store", None)
    return ProductOut(
        id=p.id,
        store_id=p.store_id,
        name=p.name,
        category=p.category,
        price=float(p.price) if p.price is not None else None,
        species=p.species,
        min_weight_kg=p.min_weight_kg,
        max_weight_kg=p.max_weight_kg,
        spec=p.spec,
        image_url=p.image_url,
        description=p.description,
        is_active=p.is_active,
        created_at=p.created_at,
        store_name=s.name if s else None,
        store_phone=s.phone if s else None,
        store_address=s.address if s else None,
        store_city=s.city if s else None,
        store_rating=s.rating if s else None,
        stock=getattr(p, "stock", 0) or 0,
        promo=getattr(p, "promo", None),
        shipping_mode=getattr(p, "shipping_mode", None) or "instant",
        brand=getattr(p, "brand", None),
        package_spec=getattr(p, "package_spec", None),
    )


async def _require_admin(user: User) -> None:
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="需要管理员权限")


async def _can_manage_staff(user: User, store_id: int) -> bool:
    """店员管理权限：超管，或该店店主(manager)。"""
    if is_admin(user):
        return True
    return (
        user.role == "staff"
        and user.store_id == store_id
        and user.staff_role == "manager"
    )


async def _resolve_staff_for_product(user: User) -> int | None:
    """返回商品归属的 store_id 约束：仅本店 staff；超管不可上架（商品归属商家）。"""
    if user.role == "staff" and user.store_id is not None:
        return user.store_id
    raise HTTPException(status_code=403, detail="仅本店商家可以上架或管理商品")


async def _find_product_for(user: User, product_id: int) -> Product:
    store_id = await _resolve_staff_for_product(user)
    try:
        return await Product.get(id=product_id, store_id=store_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="商品不存在")


# ---------------------------------------------------------------------------
# 门店
# ---------------------------------------------------------------------------


@router.get("", response_model=list[StoreOut])
async def list_stores(
    user: User = Depends(get_current_user),
    store_type: str | None = Query(None),
    city: str | None = Query(None),
):
    q = Store.all()
    if store_type:
        q = q.filter(store_type=store_type)
    if city:
        q = q.filter(city__icontains=city)
    return await q.order_by("-rating", "-id")


@router.post("", response_model=StoreOut)
async def create_store(data: StoreIn, user: User = Depends(get_current_user)):
    await _require_admin(user)
    return await Store.create(
        name=data.name,
        store_type=data.store_type,
        address=data.address,
        phone=data.phone,
        city=data.city,
        description=data.description,
    )


@router.delete("/{store_id}")
async def delete_store(store_id: int, user: User = Depends(get_current_user)):
    await _require_admin(user)
    try:
        store = await Store.get(id=store_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="门店不存在")
    # 关联商品与店员一并清理
    await Product.filter(store=store).delete()
    await User.filter(store=store).update(store=None, staff_role=None, role="user")
    await store.delete()
    return {"detail": "已删除"}


# ---------------------------------------------------------------------------
# 店员管理（超管分配）
# ---------------------------------------------------------------------------


@router.get("/{store_id}/staff", response_model=list[StaffOut])
async def list_staff(store_id: int, user: User = Depends(get_current_user)):
    if not await _can_manage_staff(user, store_id):
        raise HTTPException(status_code=403, detail="需要超管或店主权限")
    store = await Store.get_or_none(id=store_id)
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    return await User.filter(store=store, role="staff").order_by("-staff_role", "id")


@router.get("/{store_id}/staff/search")
async def search_staff_candidates(
    store_id: int,
    username: str = Query(..., min_length=1),
    user: User = Depends(get_current_user),
):
    """按用户名搜索可被加为店员的用户（排除已是其他店 staff 的）。"""
    if not await _can_manage_staff(user, store_id):
        raise HTTPException(status_code=403, detail="需要超管或店主权限")
    store = await Store.get_or_none(id=store_id)
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    candidates = []
    for u in await User.filter(username__icontains=username).limit(10):
        if u.id == user.id:
            continue
        if u.role == "staff" and u.store_id and u.store_id != store_id:
            continue
        candidates.append({"id": u.id, "username": u.username, "email": u.email})
    return candidates


@router.post("/{store_id}/staff", response_model=StaffOut)
async def assign_staff(
    store_id: int, data: StaffAssignIn, user: User = Depends(get_current_user)
):
    if not await _can_manage_staff(user, store_id):
        raise HTTPException(status_code=403, detail="需要超管或店主权限")
    store = await Store.get_or_none(id=store_id)
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    # 医院端一人一账号即可，不设店员层级
    if store.store_type == "hospital":
        raise HTTPException(status_code=400, detail="宠物医院不设职工账号，由医院端账号统一处理预约")
    if data.staff_role not in STAFF_ROLES:
        raise HTTPException(status_code=400, detail="staff_role 应为 manager 或 assistant")
    # 本店店主只能添加普通店员，不能新增店主
    if not is_admin(user) and data.staff_role == "manager":
        raise HTTPException(status_code=403, detail="只有超管可以指定店主")
    target = await User.get_or_none(id=data.user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    # 一个用户只能属于一家店；如需换店先解除
    if target.role == "staff" and target.store_id and target.store_id != store_id:
        raise HTTPException(status_code=400, detail="该用户已是其他门店店员，请先解除")
    target.role = "staff"
    target.store = store
    target.staff_role = data.staff_role
    await target.save(update_fields=["role", "store_id", "staff_role"])
    return target


@router.delete("/{store_id}/staff/{staff_id}")
async def remove_staff(store_id: int, staff_id: int, user: User = Depends(get_current_user)):
    if not await _can_manage_staff(user, store_id):
        raise HTTPException(status_code=403, detail="需要超管或店主权限")
    store = await Store.get_or_none(id=store_id)
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    target = await User.get_or_none(id=staff_id, store=store, role="staff")
    if not target:
        raise HTTPException(status_code=404, detail="该门店店员不存在")
    # 店主不能解除自己；超管可以
    if target.id == user.id and not is_admin(user):
        raise HTTPException(status_code=400, detail="不能解除自己的店主身份")
    target.role = "user"
    target.store = None
    target.staff_role = None
    await target.save(update_fields=["role", "store_id", "staff_role"])
    return {"detail": "已解除店员身份"}


# ---------------------------------------------------------------------------
# 商品（一期仅展示 + AI 导购，不做订单支付）
# ---------------------------------------------------------------------------


@router.get("/products", response_model=list[ProductOut])
async def list_products(
    user: User = Depends(get_current_user),
    category: str | None = Query(None),
    species: str | None = Query(None),
    keyword: str | None = Query(None),
    store_id: int | None = Query(None, description="按门店筛选；不传则返回全部在售"),
):
    q = Product.filter(is_active=True)
    if category:
        if category not in PRODUCT_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"未知分类: {category}")
        q = q.filter(category=category)
    if species:
        q = q.filter(species__in=["both", species])
    if keyword:
        q = q.filter(name__icontains=keyword)
    if store_id:
        q = q.filter(store_id=store_id)
    items = await q.prefetch_related("store").order_by("-id")
    return [to_product_out(p) for p in items]


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: int, user: User = Depends(get_current_user)):
    try:
        p = await Product.get(id=product_id, is_active=True)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="商品不存在")
    await p.fetch_related("store")
    return to_product_out(p)


@router.post("/products", response_model=ProductOut)
async def create_product(data: ProductIn, user: User = Depends(get_current_user)):
    allowed_store_id = await _resolve_staff_for_product(user)
    if data.category not in PRODUCT_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"未知分类: {data.category}")
    store = None
    if data.store_id:
        store = await Store.get_or_none(id=data.store_id)
        if not store:
            raise HTTPException(status_code=400, detail="门店不存在")
        if allowed_store_id is not None and store.id != allowed_store_id:
            raise HTTPException(status_code=403, detail="只能管理本店商品")
    elif allowed_store_id is not None:
        store = await Store.get_or_none(id=allowed_store_id)
    p = await Product.create(
        store=store,
        name=data.name,
        category=data.category,
        price=Decimal(str(data.price)) if data.price is not None else None,
        species=data.species,
        min_weight_kg=data.min_weight_kg,
        max_weight_kg=data.max_weight_kg,
        spec=data.spec,
        image_url=data.image_url,
        description=data.description,
        is_active=data.is_active,
        stock=data.stock,
        promo=data.promo,
        shipping_mode=data.shipping_mode or "instant",
        brand=data.brand,
        package_spec=data.package_spec,
    )
    await p.fetch_related("store")
    return to_product_out(p)


@router.put("/products/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int, data: ProductIn, user: User = Depends(get_current_user)
):
    p = await _find_product_for(user, product_id)
    allowed_store_id = await _resolve_staff_for_product(user)
    store = None
    if data.store_id:
        store = await Store.get_or_none(id=data.store_id)
        if not store:
            raise HTTPException(status_code=400, detail="门店不存在")
        if allowed_store_id is not None and store.id != allowed_store_id:
            raise HTTPException(status_code=403, detail="只能管理本店商品")
    elif allowed_store_id is not None:
        store = await Store.get_or_none(id=allowed_store_id)
    p.name = data.name
    p.store = store
    p.category = data.category
    p.price = Decimal(str(data.price)) if data.price is not None else None
    p.species = data.species
    p.min_weight_kg = data.min_weight_kg
    p.max_weight_kg = data.max_weight_kg
    p.spec = data.spec
    p.image_url = data.image_url
    p.description = data.description
    p.is_active = data.is_active
    p.stock = data.stock
    p.promo = data.promo
    p.shipping_mode = data.shipping_mode or "instant"
    p.brand = data.brand
    p.package_spec = data.package_spec
    await p.save()
    await p.fetch_related("store")
    return to_product_out(p)


@router.delete("/products/{product_id}")
async def delete_product(product_id: int, user: User = Depends(get_current_user)):
    p = await _find_product_for(user, product_id)
    await p.delete()
    return {"detail": "已删除"}
