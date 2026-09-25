from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from tortoise.exceptions import DoesNotExist

from app.api.auth import get_current_user
from app.api.store import to_product_out
from app.models.models import (
    Appointment,
    BoardingReservation,
    Document,
    KnowledgeBase,
    Pet,
    Product,
    Store,
    User,
    VaccineRecord,
)
from app.schemas.schemas import (
    AppointmentOut,
    AppointmentStatusIn,
    BoardingOut,
    BoardingStatusIn,
    CustomerOut,
    CustomerPetOut,
    DocumentOut,
    KnowledgeBaseOut,
    ProductOut,
    StoreOverviewOut,
    VaccineInviteIn,
    VaccineRecallOut,
)

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

APPT_STATUS = {"pending", "confirmed", "completed", "cancelled"}
BOARDING_STATUS = {"pending", "confirmed", "completed", "cancelled"}


async def get_store_staff(user: User = Depends(get_current_user)) -> User:
    """店端认证：必须是绑定了门店的 staff。"""
    if user.role != "staff" or user.store_id is None:
        raise HTTPException(status_code=403, detail="需要门店店员身份")
    return user


async def get_store_manager(user: User = Depends(get_store_staff)) -> User:
    """店主权限：必须是本店 manager。"""
    if user.staff_role != "manager":
        raise HTTPException(status_code=403, detail="需要店主权限")
    return user


async def _get_store(user: User) -> Store:
    store = await Store.get_or_none(id=user.store_id)
    if not store:
        raise HTTPException(status_code=403, detail="所属门店不存在")
    return store


async def _store_related_ids(store_id: int) -> tuple[list[int], set[int]]:
    appt_users = await Appointment.filter(store_id=store_id).distinct().values_list("user_id", flat=True)
    board_users = await BoardingReservation.filter(store_id=store_id).distinct().values_list(
        "user_id", flat=True
    )
    appt_pets = await Appointment.filter(store_id=store_id, pet_id__not_isnull=True).values_list(
        "pet_id", flat=True
    )
    board_pets = await BoardingReservation.filter(store_id=store_id).values_list("pet_id", flat=True)
    user_ids = list(set(appt_users) | set(board_users))
    pet_ids = {p for p in list(appt_pets) + list(board_pets) if p}
    return user_ids, pet_ids


# ---------------------------------------------------------------------------
# 本店内容库
# ---------------------------------------------------------------------------


async def _get_store_kb(user: User) -> KnowledgeBase:
    """返回本店的内容库；不存在则自动创建一个（归属超管，绑定本门店）。"""
    store = await _get_store(user)
    kb = await KnowledgeBase.get_or_none(store=store)
    if kb:
        return kb
    owner = await User.filter(role="admin").first()
    return await KnowledgeBase.create(
        name=f"{store.name}内容库",
        description=f"门店「{store.name}」的内部资料库：服务条款、寄养细则、商品说明、SOP 等",
        owner=owner,
        store=store,
        is_public=False,
    )


@router.get("/kb", response_model=KnowledgeBaseOut)
async def store_kb(user: User = Depends(get_store_staff)):
    return await _get_store_kb(user)


@router.get("/kb/documents", response_model=list[DocumentOut])
async def store_kb_documents(user: User = Depends(get_store_staff)):
    kb = await _get_store_kb(user)
    return await Document.filter(kb=kb).order_by("-id")


# ---------------------------------------------------------------------------
# 工作台概览
# ---------------------------------------------------------------------------


@router.get("/overview", response_model=StoreOverviewOut)
async def overview(user: User = Depends(get_store_staff)):
    store = await _get_store(user)
    staff_count = await User.filter(store=store, role="staff").count()
    pending_appts = await Appointment.filter(store=store, status="pending").count()
    active_boardings = await BoardingReservation.filter(
        store=store, status__in=["pending", "confirmed"]
    ).count()
    products = await Product.filter(store=store).count()
    user_ids, pet_ids = await _store_related_ids(store.id)
    customers = len(user_ids)
    due = 0
    if pet_ids:
        today = date.today()
        due = await VaccineRecord.filter(
            pet_id__in=list(pet_ids),
            next_due_date__not_isnull=True,
            next_due_date__lte=today + timedelta(days=30),
        ).count()
    return StoreOverviewOut(
        store=store,
        staff=staff_count,
        pending_appointments=pending_appts,
        active_boardings=active_boardings,
        customers=customers,
        products=products,
        due_vaccines=due,
    )


# ---------------------------------------------------------------------------
# 预约处理台
# ---------------------------------------------------------------------------


@router.get("/appointments", response_model=list[AppointmentOut])
async def list_appointments(
    user: User = Depends(get_store_staff),
    status: str | None = None,
):
    from app.api.booking import appointment_out

    q = Appointment.filter(store_id=user.store_id)
    if status:
        if status not in APPT_STATUS:
            raise HTTPException(status_code=400, detail=f"未知状态: {status}")
        q = q.filter(status=status)
    rows = await q.prefetch_related("store", "pet", "user", "trainer").order_by("appt_time")
    return [appointment_out(a) for a in rows]


@router.post("/appointments/{appt_id}/status")
async def update_appointment(
    appt_id: int, data: AppointmentStatusIn, user: User = Depends(get_store_staff)
):
    if data.status not in APPT_STATUS:
        raise HTTPException(status_code=400, detail=f"未知状态: {data.status}")
    try:
        appt = await Appointment.get(id=appt_id, store_id=user.store_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="预约不存在")
    appt.status = data.status
    await appt.save(update_fields=["status"])
    return {"detail": "已更新"}


# ---------------------------------------------------------------------------
# 寄养排期管理
# ---------------------------------------------------------------------------


@router.get("/boardings", response_model=list[BoardingOut])
async def list_boardings(
    user: User = Depends(get_store_staff),
    status: str | None = None,
):
    q = BoardingReservation.filter(store_id=user.store_id)
    if status:
        if status not in BOARDING_STATUS:
            raise HTTPException(status_code=400, detail=f"未知状态: {status}")
        q = q.filter(status=status)
    return await q.order_by("start_date")


@router.post("/boardings/{boarding_id}/status")
async def update_boarding(
    boarding_id: int, data: BoardingStatusIn, user: User = Depends(get_store_staff)
):
    if data.status not in BOARDING_STATUS:
        raise HTTPException(status_code=400, detail=f"未知状态: {data.status}")
    try:
        b = await BoardingReservation.get(id=boarding_id, store_id=user.store_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="寄养订单不存在")
    b.status = data.status
    await b.save(update_fields=["status"])
    return {"detail": "已更新"}


# ---------------------------------------------------------------------------
# 客户档案
# ---------------------------------------------------------------------------


@router.get("/customers", response_model=list[CustomerOut])
async def list_customers(user: User = Depends(get_store_staff)):
    appt_users = await Appointment.filter(store_id=user.store_id).distinct().values_list(
        "user_id", flat=True
    )
    board_users = (
        await BoardingReservation.filter(store_id=user.store_id)
        .distinct()
        .values_list("user_id", flat=True)
    )
    user_ids, pet_ids = await _store_related_ids(user.store_id)
    if not user_ids:
        return []
    users = await User.filter(id__in=user_ids)
    result = []
    for u in users:
        pets = await Pet.filter(owner=u, id__in=list(pet_ids)) if pet_ids else []
        last_appt = (
            await Appointment.filter(user=u, store_id=user.store_id)
            .order_by("-appt_time")
            .first()
        )
        result.append(
            CustomerOut(
                id=u.id,
                username=u.username,
                email=u.email,
                pets=[CustomerPetOut(id=p.id, name=p.name, species=p.species, breed=p.breed) for p in pets],
                last_appointment_at=last_appt.appt_time if last_appt else None,
            )
        )
    return result


@router.get("/products", response_model=list[ProductOut])
async def workspace_products(user: User = Depends(get_store_staff)):
    items = await Product.filter(store_id=user.store_id).prefetch_related("store").order_by("-id")
    return [to_product_out(p) for p in items]


@router.get("/vaccine-recalls", response_model=list[VaccineRecallOut])
async def vaccine_recalls(days: int = 30, user: User = Depends(get_store_staff)):
    _, pet_ids = await _store_related_ids(user.store_id)
    if not pet_ids:
        return []
    today = date.today()
    limit = today + timedelta(days=days)
    rows = await VaccineRecord.filter(
        pet_id__in=list(pet_ids),
        next_due_date__not_isnull=True,
        next_due_date__lte=limit,
    ).prefetch_related("pet", "pet__owner").order_by("next_due_date")
    out = []
    for v in rows:
        pet = v.pet
        owner = pet.owner
        days_left = (v.next_due_date - today).days
        out.append(
            VaccineRecallOut(
                vaccine_id=v.id,
                pet_id=pet.id,
                pet_name=pet.name,
                species=pet.species,
                owner_id=owner.id,
                owner_name=owner.username,
                vaccine_name=v.vaccine_name,
                dose_no=v.dose_no,
                next_due_date=v.next_due_date,
                status="overdue" if days_left < 0 else "due_soon",
                days_left=days_left,
            )
        )
    return out


@router.post("/vaccine-recalls/invite", response_model=AppointmentOut)
async def invite_vaccine(data: VaccineInviteIn, user: User = Depends(get_store_staff)):
    """宠物店疫苗中转：帮客户在医院生成就诊预约，本店不承担接种。"""
    from app.api.booking import appointment_out

    store = await Store.get_or_none(id=user.store_id)
    if not store:
        raise HTTPException(status_code=403, detail="所属门店不存在")

    # 医院端自己处理就诊预约即可，不走「代约中转」
    if store.store_type == "hospital":
        raise HTTPException(status_code=400, detail="医院请直接在预约处理台确认用户就诊单，无需代约中转")

    _, pet_ids = await _store_related_ids(user.store_id)
    if data.pet_id not in pet_ids:
        raise HTTPException(status_code=404, detail="该宠物不是本店客户")
    pet = await Pet.filter(id=data.pet_id).prefetch_related("owner").first()
    if not pet:
        raise HTTPException(status_code=404, detail="宠物不存在")

    if not data.hospital_id:
        raise HTTPException(status_code=400, detail="请选择代约的接种医院（宠物店仅作中转，不在本店接种）")
    hospital = await Store.get_or_none(id=data.hospital_id, store_type="hospital")
    if not hospital:
        raise HTTPException(status_code=400, detail="目标医院不存在或类型不是宠物医院")

    if data.appt_time:
        try:
            t = datetime.fromisoformat(data.appt_time.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            raise HTTPException(status_code=400, detail="appt_time 格式应为 ISO 时间")
    else:
        t = datetime.combine(date.today() + timedelta(days=2), datetime.min.time().replace(hour=10))

    vaccine_bit = ""
    if data.vaccine_id:
        rec = await VaccineRecord.get_or_none(id=data.vaccine_id, pet_id=pet.id)
        if rec and rec.next_due_date:
            vaccine_bit = f"{rec.vaccine_name}（到期 {rec.next_due_date.isoformat()}）"
        elif rec:
            vaccine_bit = rec.vaccine_name

    notes_parts = [
        f"【宠物店代约中转】由「{store.name}」协助预约接种",
        f"疫苗：{vaccine_bit}" if vaccine_bit else "疫苗临期召回",
        data.notes.strip() if data.notes else "",
    ]
    notes = "；".join(p for p in notes_parts if p)

    appt = await Appointment.create(
        user_id=pet.owner_id,
        pet=pet,
        store=hospital,
        appt_type="exam",
        appt_time=t,
        notes=notes,
        status="pending",
    )
    await appt.fetch_related("store", "pet")
    return appointment_out(appt)