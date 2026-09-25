"""商品订单：用户下单，门店履约（一期无第三方支付）。"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.models.models import Order, OrderItem, Product, User
from app.schemas.schemas import OrderIn, OrderItemOut, OrderOut, OrderStatusIn

router = APIRouter(prefix="/api/orders", tags=["orders"])

USER_VISIBLE = {"pending", "accepted", "preparing", "delivering", "completed", "cancelled"}
NEXT_STATUS = {
    "pending": {"accepted", "cancelled"},
    "accepted": {"preparing", "cancelled"},
    "preparing": {"delivering", "cancelled"},
    "delivering": {"completed"},
}


def _to_out(order: Order, items: list[OrderItem] | None = None) -> OrderOut:
    s = getattr(order, "store", None)
    rows = items if items is not None else []
    return OrderOut(
        id=order.id,
        user_id=order.user_id,
        store_id=order.store_id,
        store_name=s.name if s else None,
        status=order.status,
        shipping_mode=order.shipping_mode,
        address=order.address,
        total=float(order.total or 0),
        notes=order.notes,
        items=[
            OrderItemOut(
                id=i.id,
                product_id=i.product_id,
                name=i.name,
                qty=i.qty,
                price=float(i.price or 0),
            )
            for i in rows
        ],
        created_at=order.created_at,
    )


async def _load_out(order: Order) -> OrderOut:
    await order.fetch_related("store")
    items = await OrderItem.filter(order=order)
    return _to_out(order, items)


@router.post("", response_model=OrderOut)
async def create_order(data: OrderIn, user: User = Depends(get_current_user)):
    if not data.items:
        raise HTTPException(status_code=400, detail="请至少选择一件商品")
    if not (data.address or "").strip():
        raise HTTPException(status_code=400, detail="请填写配送地址")

    products: list[tuple[Product, int]] = []
    store_id = None
    for it in data.items:
        if it.qty < 1:
            raise HTTPException(status_code=400, detail="数量须大于 0")
        p = await Product.get_or_none(id=it.product_id, is_active=True)
        if not p:
            raise HTTPException(status_code=400, detail=f"商品不存在或已下架: {it.product_id}")
        if p.stock < it.qty:
            raise HTTPException(status_code=400, detail=f"「{p.name}」库存不足")
        if p.store_id is None:
            raise HTTPException(status_code=400, detail=f"「{p.name}」未绑定门店，无法下单")
        if store_id is None:
            store_id = p.store_id
        elif p.store_id != store_id:
            raise HTTPException(status_code=400, detail="一笔订单只能购买同一家店的商品")
        products.append((p, it.qty))

    total = Decimal("0")
    ship = data.shipping_mode or products[0][0].shipping_mode or "instant"
    order = await Order.create(
        user=user,
        store_id=store_id,
        status="pending",
        shipping_mode=ship,
        address=data.address.strip(),
        notes=data.notes,
        total=0,
    )
    for p, qty in products:
        price = Decimal(str(p.price or 0))
        total += price * qty
        p.stock -= qty
        await p.save(update_fields=["stock"])
        await OrderItem.create(order=order, product=p, name=p.name, qty=qty, price=price)
    order.total = total
    await order.save(update_fields=["total"])
    user.points = (user.points or 0) + int(total)
    await user.save(update_fields=["points"])
    return await _load_out(order)


@router.get("", response_model=list[OrderOut])
async def my_orders(user: User = Depends(get_current_user)):
    rows = await Order.filter(user=user).prefetch_related("store").order_by("-id")
    return [await _load_out(o) for o in rows]


@router.post("/{order_id}/cancel")
async def cancel_order(order_id: int, user: User = Depends(get_current_user)):
    order = await Order.get_or_none(id=order_id, user=user)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status not in ("pending", "accepted"):
        raise HTTPException(status_code=400, detail="当前状态不可取消")
    await _restore_stock(order)
    order.status = "cancelled"
    await order.save(update_fields=["status"])
    return {"detail": "已取消"}


@router.get("/store", response_model=list[OrderOut])
async def store_orders(user: User = Depends(get_current_user)):
    if user.role != "staff" or not user.store_id:
        raise HTTPException(status_code=403, detail="需要门店店员身份")
    rows = await Order.filter(store_id=user.store_id).prefetch_related("store").order_by("-id")
    return [await _load_out(o) for o in rows]


@router.post("/{order_id}/status", response_model=OrderOut)
async def update_status(order_id: int, data: OrderStatusIn, user: User = Depends(get_current_user)):
    if user.role != "staff" or not user.store_id:
        raise HTTPException(status_code=403, detail="需要门店店员身份")
    order = await Order.get_or_none(id=order_id, store_id=user.store_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    allowed = NEXT_STATUS.get(order.status, set())
    if data.status not in allowed:
        raise HTTPException(status_code=400, detail=f"不能从 {order.status} 变为 {data.status}")
    if data.status == "cancelled":
        await _restore_stock(order)
    order.status = data.status
    await order.save(update_fields=["status"])
    return await _load_out(order)


async def _restore_stock(order: Order) -> None:
    items = await OrderItem.filter(order=order)
    for i in items:
        if not i.product_id:
            continue
        p = await Product.get_or_none(id=i.product_id)
        if p:
            p.stock += i.qty
            await p.save(update_fields=["stock"])
