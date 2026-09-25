from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from tortoise.exceptions import DoesNotExist

from app.api.auth import get_current_user
from app.models.models import MedicalExam, MedicationRecord, Pet, User, VaccineRecord
from app.schemas.schemas import PetIn, PetOut, VaccineIn, VaccineOut

router = APIRouter(prefix="/api/pets", tags=["pets"])


def _parse_date(value: str | None, field: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field} 格式应为 YYYY-MM-DD")


async def _get_owned_pet(pet_id: int, user: User) -> Pet:
    try:
        pet = await Pet.get(id=pet_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="宠物不存在")
    if pet.owner_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该宠物")
    return pet


def _pet_values(data: PetIn) -> dict:
    return {
        "name": data.name.strip(),
        "species": data.species,
        "breed": data.breed,
        "gender": data.gender,
        "birth_date": _parse_date(data.birth_date, "birth_date"),
        "weight_kg": data.weight_kg,
        "chip_no": data.chip_no,
        "is_neutered": data.is_neutered,
        "nickname": (data.nickname or "").strip(),
        "color": data.color,
        "activity_level": data.activity_level or "medium",
        "diet": data.diet or "",
        "allergies": data.allergies or "",
        "chronic_conditions": data.chronic_conditions or "",
        "temperament": data.temperament,
        "living_env": data.living_env or "indoor",
        "city": data.city,
        "notes": data.notes or "",
        "image_url": data.image_url,
    }


@router.post("", response_model=PetOut)
async def create_pet(data: PetIn, user: User = Depends(get_current_user)):
    pet = await Pet.create(owner=user, **_pet_values(data))
    return pet


@router.get("", response_model=list[PetOut])
async def list_pets(user: User = Depends(get_current_user)):
    return await Pet.filter(owner=user).order_by("-id")


@router.get("/{pet_id}", response_model=PetOut)
async def get_pet(pet_id: int, user: User = Depends(get_current_user)):
    return await _get_owned_pet(pet_id, user)


@router.put("/{pet_id}", response_model=PetOut)
async def update_pet(pet_id: int, data: PetIn, user: User = Depends(get_current_user)):
    pet = await _get_owned_pet(pet_id, user)
    for key, value in _pet_values(data).items():
        setattr(pet, key, value)
    await pet.save()
    return pet


@router.delete("/{pet_id}")
async def delete_pet(pet_id: int, user: User = Depends(get_current_user)):
    pet = await _get_owned_pet(pet_id, user)
    await VaccineRecord.filter(pet=pet).delete()
    await pet.delete()
    return {"detail": "已删除"}


# ---------------------------------------------------------------------------
# 疫苗记录（挂在宠物下；独立操作按 pet_id 归属校验）
# ---------------------------------------------------------------------------


@router.post("/{pet_id}/vaccines", response_model=VaccineOut)
async def add_vaccine(pet_id: int, data: VaccineIn, user: User = Depends(get_current_user)):
    pet = await _get_owned_pet(pet_id, user)
    v = await VaccineRecord.create(
        pet=pet,
        vaccine_name=data.vaccine_name,
        dose_no=data.dose_no,
        vaccinated_at=_parse_date(data.vaccinated_at, "vaccinated_at") or date.today(),
        next_due_date=_parse_date(data.next_due_date, "next_due_date"),
        notes=data.notes,
    )
    return v


@router.get("/{pet_id}/vaccines", response_model=list[VaccineOut])
async def list_vaccines(pet_id: int, user: User = Depends(get_current_user)):
    pet = await _get_owned_pet(pet_id, user)
    return await VaccineRecord.filter(pet=pet).order_by("-vaccinated_at")


@router.get("/{pet_id}/vaccines/upcoming", response_model=list[VaccineOut])
async def upcoming_vaccines(
    pet_id: int,
    days: int = 30,
    user: User = Depends(get_current_user),
):
    """即将到期（未来 days 天内）或已过期未补的疫苗，供提醒使用。"""
    pet = await _get_owned_pet(pet_id, user)
    today = date.today()
    limit = today + timedelta(days=days)
    return await VaccineRecord.filter(
        pet=pet, next_due_date__not_isnull=True, next_due_date__lte=limit
    ).order_by("next_due_date")


@router.put("/vaccines/{vid}", response_model=VaccineOut)
async def update_vaccine(vid: int, data: VaccineIn, user: User = Depends(get_current_user)):
    try:
        v = await VaccineRecord.get(id=vid).prefetch_related("pet")
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="疫苗记录不存在")
    if v.pet.owner_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该记录")
    v.vaccine_name = data.vaccine_name
    v.dose_no = data.dose_no
    v.vaccinated_at = _parse_date(data.vaccinated_at, "vaccinated_at") or v.vaccinated_at
    v.next_due_date = _parse_date(data.next_due_date, "next_due_date")
    v.notes = data.notes
    await v.save()
    return v


@router.delete("/vaccines/{vid}")
async def delete_vaccine(vid: int, user: User = Depends(get_current_user)):
    try:
        v = await VaccineRecord.get(id=vid).prefetch_related("pet")
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="疫苗记录不存在")
    if v.pet.owner_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该记录")
    await v.delete()
    return {"detail": "已删除"}


# ---------------------------------------------------------------------------
# 智能体工具执行辅助（只读，供 agent_service 调用）
# ---------------------------------------------------------------------------


async def resolve_owned_pet(
    user: User,
    pet_id: int | None = None,
    name: str | None = None,
    bound_pet_id: int | None = None,
) -> tuple[Pet | None, dict | None]:
    """解析当前用户的宠物：显式 ID/名称 > 问答绑定 > 仅有一只时默认。"""
    qs = Pet.filter(owner=user)
    if pet_id:
        pet = await qs.filter(id=pet_id).first()
        if not pet:
            return None, {"error": f"未找到您的宠物（id={pet_id}）"}
        return pet, None
    if name:
        hits = await qs.filter(name=name)
        if not hits:
            nick = await qs.filter(nickname=name).first()
            if nick:
                return nick, None
            return None, {"error": f"未找到您的宠物（name={name}）"}
        if len(hits) == 1:
            return hits[0], None
        if bound_pet_id:
            bound = next((p for p in hits if p.id == bound_pet_id), None)
            if bound:
                return bound, None
        return None, {
            "error": f"您有多只都叫「{name}」的宠物，请用昵称、品种、生日区分，或在问答页下拉选择",
            "candidates": [_pet_brief(p) for p in hits],
        }
    if bound_pet_id:
        pet = await qs.filter(id=bound_pet_id).first()
        if pet:
            return pet, None
    pets = await qs.order_by("-id")
    if len(pets) == 1:
        return pets[0], None
    if not pets:
        return None, {"error": "您还没有宠物档案，请先在「我的宠物」中添加"}
    return None, {
        "error": "您有多只宠物，请先在问答页选择当前宠物，或提供宠物名/昵称",
        "pets": [_pet_brief(p) for p in pets],
    }


def _age_months(birth: date | None) -> int | None:
    if not birth:
        return None
    today = date.today()
    months = (today.year - birth.year) * 12 + today.month - birth.month
    if today.day < birth.day:
        months -= 1
    return max(months, 0)


def _pet_brief(pet: Pet) -> dict:
    months = _age_months(pet.birth_date)
    return {
        "id": pet.id,
        "name": pet.name,
        "nickname": pet.nickname or "",
        "species": pet.species,
        "breed": pet.breed,
        "gender": pet.gender,
        "birth_date": pet.birth_date.isoformat() if pet.birth_date else None,
        "age_months": months,
        "weight_kg": pet.weight_kg,
        "chip_no": pet.chip_no,
        "is_neutered": pet.is_neutered,
        "color": pet.color,
        "activity_level": pet.activity_level,
        "diet": pet.diet,
        "allergies": pet.allergies,
        "chronic_conditions": pet.chronic_conditions,
        "temperament": pet.temperament,
        "living_env": pet.living_env,
        "city": pet.city,
        "notes": pet.notes,
        "image_url": getattr(pet, "image_url", None),
    }


async def pet_profile_for_agent(user: User, pet_id: int) -> dict:
    """绑定宠物的完整上下文，写入系统提示，供个性化方案使用。"""
    pet, err = await resolve_owned_pet(user, pet_id, None, pet_id)
    if err:
        return err
    vac = await lookup_vaccines(user, pet.id, pet.id)
    health = await lookup_health(user, pet.id, pet.id)
    return {
        "profile": _pet_brief(pet),
        "vaccines": vac.get("vaccines", []),
        "exams": health.get("exams", []),
        "medications": health.get("medications", []),
    }


async def lookup_pet(
    user: User,
    pet_id: int | None = None,
    name: str | None = None,
    bound_pet_id: int | None = None,
) -> dict:
    pet, err = await resolve_owned_pet(user, pet_id, name, bound_pet_id)
    if err:
        return err
    return _pet_brief(pet)


async def lookup_vaccines(
    user: User, pet_id: int | None = None, bound_pet_id: int | None = None
) -> dict:
    pet, err = await resolve_owned_pet(user, pet_id, None, bound_pet_id)
    if err:
        return err
    today = date.today()
    records = []
    for v in await VaccineRecord.filter(pet=pet).order_by("-vaccinated_at"):
        records.append(
            {
                "vaccine_name": v.vaccine_name,
                "dose_no": v.dose_no,
                "vaccinated_at": v.vaccinated_at.isoformat(),
                "next_due_date": v.next_due_date.isoformat() if v.next_due_date else None,
                "status": (
                    "overdue"
                    if v.next_due_date and v.next_due_date < today
                    else "due_soon"
                    if v.next_due_date and (v.next_due_date - today).days <= 30
                    else "ok"
                ),
            }
        )
    return {"pet_id": pet.id, "pet_name": pet.name, "vaccines": records}


async def lookup_health(
    user: User, pet_id: int | None = None, bound_pet_id: int | None = None
) -> dict:
    """查询宠物体检记录与用药记录（供 AI 回答"体检过吗/用过什么药"）。"""
    pet, err = await resolve_owned_pet(user, pet_id, None, bound_pet_id)
    if err:
        return err
    exams = [
        {
            "exam_date": e.exam_date.isoformat(),
            "hospital": e.hospital,
            "items": e.items,
            "result": e.result,
            "vet_name": e.vet_name,
        }
        for e in await MedicalExam.filter(pet=pet).order_by("-exam_date")
    ]
    meds = [
        {
            "drug_name": m.drug_name,
            "start_date": m.start_date.isoformat() if m.start_date else None,
            "end_date": m.end_date.isoformat() if m.end_date else None,
            "dosage": m.dosage,
            "reason": m.reason,
            "notes": m.notes,
        }
        for m in await MedicationRecord.filter(pet=pet).order_by("-start_date")
    ]
    return {
        "pet_id": pet.id,
        "pet_name": pet.name,
        "exams": exams,
        "medications": meds,
        "note": "体检/用药记录可能为空，表示尚未录入。",
    }


async def lookup_products(
    user: User,
    pet_id: int | None = None,
    category: str | None = None,
    bound_pet_id: int | None = None,
    store_id: int | None = None,
) -> dict:
    """商品导购：按宠物体重/物种匹配规格，并返回所属门店联系方式便于到店购买。"""
    from app.models.models import Product

    pet = None
    if pet_id is not None or bound_pet_id is not None:
        pet, err = await resolve_owned_pet(user, pet_id, None, bound_pet_id)
        if pet_id is not None and err:
            return err
        if pet_id is None and bound_pet_id and err and "多只宠物" not in (err.get("error") or ""):
            # 绑定失败时仍可按分类查商品
            pet = None

    qs = Product.filter(is_active=True)
    if category:
        qs = qs.filter(category=category)
    if store_id:
        qs = qs.filter(store_id=store_id)
    products = await qs.prefetch_related("store").order_by("-id").limit(20)

    items = []
    for p in products:
        match = True
        if pet:
            if p.species not in ("both", pet.species):
                match = False
            w = pet.weight_kg
            if match and w is not None:
                if p.min_weight_kg is not None and w < p.min_weight_kg:
                    match = False
                if p.max_weight_kg is not None and w > p.max_weight_kg:
                    match = False
        if match:
            s = getattr(p, "store", None)
            items.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "category": p.category,
                    "price": float(p.price) if p.price is not None else None,
                    "species": p.species,
                    "spec": p.spec,
                    "min_weight_kg": p.min_weight_kg,
                    "max_weight_kg": p.max_weight_kg,
                    "description": p.description,
                    "store_id": p.store_id,
        "store_name": s.name if s else None,
                    "store_phone": s.phone if s else None,
                    "store_address": s.address if s else None,
                    "store_city": s.city if s else None,
                    "stock": getattr(p, "stock", None),
                    "promo": getattr(p, "promo", None),
                    "shipping_mode": getattr(p, "shipping_mode", None),
                    "brand": getattr(p, "brand", None),
                    "package_spec": getattr(p, "package_spec", None),
                }
            )
    return {
        "pet": {
            "id": pet.id,
            "name": pet.name,
            "species": pet.species,
            "weight_kg": pet.weight_kg,
        }
        if pet
        else None,
        "category": category,
        "store_id": store_id,
        "products": items,
        "note": "平台不自营，商品归属各宠物店。比较时看评分、库存、配送、品牌包装，价格只是其中一项。",
    }
