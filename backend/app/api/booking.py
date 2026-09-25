from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from tortoise.exceptions import DoesNotExist

from app.api.auth import get_current_user
from app.api.pets import _get_owned_pet
from app.models.models import Appointment, BoardingReservation, Pet, Store, TrainerProfile, User
from app.schemas.schemas import (
    AppointmentIn,
    AppointmentOut,
    AppointmentStatusIn,
    BoardingIn,
    BoardingOut,
)

router = APIRouter(prefix="/api/booking", tags=["booking"])

APPT_TYPES = {"exam", "grooming", "boarding", "consult", "train"}
APPT_STATUS = {"pending", "confirmed", "completed", "cancelled"}
# 预约类型对应应选的门店类型（train 走训犬师，不绑门店）
APPT_STORE_TYPES = {
    "exam": {"hospital"},
    "consult": {"hospital", "shop"},
    "grooming": {"shop"},
    "boarding": {"boarding", "shop"},
}


def _parse_datetime(value: str, field: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field} 格式应为 ISO 时间")


def _parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field} 格式应为 YYYY-MM-DD")


async def _get_owned_pet_or_none(pet_id: int | None, user: User) -> Pet | None:
    if pet_id is None:
        return None
    return await _get_owned_pet(pet_id, user)


def _rel_str(obj, attr: str) -> str | None:
    """安全读取已 prefetch 的关联字段；未加载的 FK 在 Tortoise 里可能是 QuerySet。"""
    if obj is None:
        return None
    # QuerySet / 其他非 Model 不能当关联对象
    if not hasattr(obj, "id") or callable(getattr(obj, "filter", None)):
        return None
    val = getattr(obj, attr, None)
    return val if isinstance(val, str) else None


def appointment_out(a: Appointment) -> AppointmentOut:
    s = getattr(a, "store", None)
    pet = getattr(a, "pet", None)
    tr = getattr(a, "trainer", None)
    owner = getattr(a, "user", None)
    return AppointmentOut(
        id=a.id,
        user_id=a.user_id,
        pet_id=a.pet_id,
        store_id=a.store_id,
        trainer_id=getattr(a, "trainer_id", None),
        appt_type=a.appt_type,
        appt_time=a.appt_time,
        status=a.status,
        notes=a.notes,
        created_at=a.created_at,
        store_name=_rel_str(s, "name"),
        store_type=_rel_str(s, "store_type"),
        trainer_name=_rel_str(tr, "display_name"),
        pet_name=_rel_str(pet, "name"),
        user_name=_rel_str(owner, "username"),
    )


def boarding_out(b: BoardingReservation) -> BoardingOut:
    s = getattr(b, "store", None)
    pet = getattr(b, "pet", None)
    return BoardingOut(
        id=b.id,
        user_id=b.user_id,
        pet_id=b.pet_id,
        store_id=b.store_id,
        start_date=b.start_date,
        end_date=b.end_date,
        daily_fee=float(b.daily_fee) if b.daily_fee is not None else None,
        notes=b.notes,
        status=b.status,
        created_at=b.created_at,
        store_name=s.name if s else None,
        pet_name=pet.name if pet else None,
    )


# ---------------------------------------------------------------------------
# 预约（门店 / 训犬师）
# ---------------------------------------------------------------------------


@router.get("/appointments", response_model=list[AppointmentOut])
async def list_appointments(user: User = Depends(get_current_user)):
    items = (
        await Appointment.filter(user=user)
        .prefetch_related("store", "pet", "trainer", "user")
        .order_by("-appt_time")
    )
    return [appointment_out(a) for a in items]


@router.post("/appointments", response_model=AppointmentOut)
async def create_appointment(
    data: AppointmentIn, user: User = Depends(get_current_user)
):
    if user.role != "user":
        raise HTTPException(status_code=403, detail="仅养宠用户可发起预约")
    if data.appt_type not in APPT_TYPES:
        raise HTTPException(status_code=400, detail=f"未知预约类型: {data.appt_type}")

    pet = await _get_owned_pet_or_none(data.pet_id, user)
    store = None
    trainer = None

    if data.appt_type == "train":
        if not data.trainer_id:
            raise HTTPException(status_code=400, detail="请选择训犬师，预约才会推送给对方接收")
        trainer = await TrainerProfile.get_or_none(id=data.trainer_id, verified=True)
        if not trainer:
            raise HTTPException(status_code=400, detail="训犬师不存在或未通过审核")
    else:
        if not data.store_id:
            raise HTTPException(status_code=400, detail="请选择要预约的医院或门店，预约才会提交给商家")
        store = await Store.get_or_none(id=data.store_id)
        if not store:
            raise HTTPException(status_code=400, detail="门店不存在")
        allowed = APPT_STORE_TYPES.get(data.appt_type)
        if allowed and store.store_type not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"该类型请预约对应商家（当前门店类型为 {store.store_type}）",
            )

    appt = await Appointment.create(
        user=user,
        pet=pet,
        store=store,
        trainer=trainer,
        appt_type=data.appt_type,
        appt_time=_parse_datetime(data.appt_time, "appt_time"),
        notes=data.notes,
        status="pending",
    )
    await appt.fetch_related("store", "pet", "trainer", "user")
    return appointment_out(appt)


@router.post("/appointments/{appt_id}/cancel")
async def cancel_appointment(appt_id: int, user: User = Depends(get_current_user)):
    try:
        appt = await Appointment.get(id=appt_id, user=user)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="预约不存在")
    if appt.status == "completed":
        raise HTTPException(status_code=400, detail="已完成预约不可取消")
    appt.status = "cancelled"
    await appt.save()
    return {"detail": "已取消"}


# ---------------------------------------------------------------------------
# 训犬师接收预约
# ---------------------------------------------------------------------------


@router.get("/trainer/appointments", response_model=list[AppointmentOut])
async def trainer_list_appointments(
    status: str | None = Query(None),
    user: User = Depends(get_current_user),
):
    if user.role != "trainer":
        raise HTTPException(status_code=403, detail="需要训犬师身份")
    profile = await TrainerProfile.get_or_none(user=user)
    if not profile:
        raise HTTPException(status_code=400, detail="请先完善训犬师主页")
    q = Appointment.filter(trainer_id=profile.id, appt_type="train")
    if status:
        if status not in APPT_STATUS:
            raise HTTPException(status_code=400, detail=f"未知状态: {status}")
        q = q.filter(status=status)
    rows = await q.prefetch_related("store", "pet", "trainer", "user").order_by("appt_time")
    return [appointment_out(a) for a in rows]


@router.post("/trainer/appointments/{appt_id}/status", response_model=AppointmentOut)
async def trainer_set_status(
    appt_id: int,
    data: AppointmentStatusIn,
    user: User = Depends(get_current_user),
):
    if user.role != "trainer":
        raise HTTPException(status_code=403, detail="需要训犬师身份")
    if data.status not in APPT_STATUS:
        raise HTTPException(status_code=400, detail=f"未知状态: {data.status}")
    profile = await TrainerProfile.get_or_none(user=user)
    if not profile:
        raise HTTPException(status_code=400, detail="请先完善训犬师主页")
    appt = await Appointment.get_or_none(id=appt_id, trainer_id=profile.id, appt_type="train")
    if not appt:
        raise HTTPException(status_code=404, detail="预约不存在")
    appt.status = data.status
    await appt.save(update_fields=["status"])
    await appt.fetch_related("store", "pet", "trainer", "user")
    return appointment_out(appt)


# ---------------------------------------------------------------------------
# 寄养预订
# ---------------------------------------------------------------------------


@router.get("/boardings", response_model=list[BoardingOut])
async def list_boardings(user: User = Depends(get_current_user)):
    items = await BoardingReservation.filter(user=user).prefetch_related("store", "pet").order_by("-start_date")
    return [boarding_out(b) for b in items]


@router.post("/boardings", response_model=BoardingOut)
async def create_boarding(data: BoardingIn, user: User = Depends(get_current_user)):
    pet = await _get_owned_pet(data.pet_id, user)
    start = _parse_date(data.start_date, "start_date")
    end = _parse_date(data.end_date, "end_date")
    if end < start:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
    if not data.store_id:
        raise HTTPException(status_code=400, detail="请选择寄养门店，预订才会提交给商家")
    store = await Store.get_or_none(id=data.store_id)
    if not store:
        raise HTTPException(status_code=400, detail="门店不存在")
    boarding = await BoardingReservation.create(
        user=user,
        pet=pet,
        store=store,
        start_date=start,
        end_date=end,
        daily_fee=data.daily_fee,
        notes=data.notes,
        status="pending",
    )
    await boarding.fetch_related("store", "pet")
    return boarding_out(boarding)


@router.post("/boardings/{boarding_id}/cancel")
async def cancel_boarding(boarding_id: int, user: User = Depends(get_current_user)):
    try:
        b = await BoardingReservation.get(id=boarding_id, user=user)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="寄养订单不存在")
    if b.status == "completed":
        raise HTTPException(status_code=400, detail="已完成寄养不可取消")
    b.status = "cancelled"
    await b.save()
    return {"detail": "已取消"}
