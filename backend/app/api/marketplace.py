"""选宠、训犬师、需求线索：平台连接层。"""
import json
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from tortoise.exceptions import DoesNotExist

from app.api.auth import get_current_user
from app.api.knowledge_base import is_admin
from app.models.models import Lead, PetListing, Store, TrainerProfile, User
from app.schemas.schemas import (
    LeadIn,
    LeadMatchIn,
    LeadOut,
    ListingIn,
    ListingOut,
    TrainerIn,
    TrainerOut,
)

router = APIRouter(prefix="/api", tags=["marketplace"])

NEED_TYPES = {"buy_pet", "product", "train", "hospital", "boarding", "consult"}
SELF_ROLES_TRAINER = "trainer"
MAX_PROOF_IMAGES = 8


def _parse_proof_images(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return [str(x).strip() for x in data if str(x).strip()][:MAX_PROOF_IMAGES]
    except Exception:
        return []


def _dump_proof_images(urls: list[str] | None) -> str:
    cleaned = [u.strip() for u in (urls or []) if u and u.strip()][:MAX_PROOF_IMAGES]
    return json.dumps(cleaned, ensure_ascii=False)


def listing_out(p: PetListing) -> ListingOut:
    s = getattr(p, "store", None)
    return ListingOut(
        id=p.id,
        store_id=p.store_id,
        store_name=s.name if s else None,
        store_phone=s.phone if s else None,
        store_address=s.address if s else None,
        store_city=s.city if s else None,
        store_rating=s.rating if s else None,
        name=p.name,
        species=p.species,
        breed=p.breed,
        gender=p.gender,
        age_months=p.age_months,
        price=float(p.price) if p.price is not None else None,
        health_note=p.health_note,
        vaccine_note=p.vaccine_note,
        description=p.description,
        appearance=getattr(p, "appearance", None) or "standard",
        color=getattr(p, "color", None),
        weight_kg=getattr(p, "weight_kg", None),
        image_url=getattr(p, "image_url", None),
        is_active=p.is_active,
        created_at=p.created_at,
    )


def trainer_out(t: TrainerProfile) -> TrainerOut:
    return TrainerOut(
        id=t.id,
        user_id=t.user_id,
        display_name=t.display_name,
        city=t.city,
        specialties=t.specialties,
        years=t.years,
        price_from=float(t.price_from) if t.price_from is not None else None,
        service_mode=t.service_mode,
        bio=t.bio,
        avatar_url=getattr(t, "avatar_url", None),
        experience=getattr(t, "experience", None) or "",
        cert_note=getattr(t, "cert_note", None) or "",
        proof_images=_parse_proof_images(getattr(t, "proof_images", None)),
        verified=t.verified,
        created_at=t.created_at,
    )


async def lead_out(lead: Lead) -> LeadOut:
    await lead.fetch_related("user", "matched_store", "matched_trainer")
    st = lead.matched_store
    tr = lead.matched_trainer
    u = lead.user
    return LeadOut(
        id=lead.id,
        user_id=lead.user_id,
        user_name=u.username if u else None,
        operator_id=lead.operator_id,
        need_type=lead.need_type,
        summary=lead.summary,
        city=lead.city,
        budget=lead.budget,
        status=lead.status,
        matched_store_id=lead.matched_store_id,
        matched_store_name=st.name if st else None,
        matched_trainer_id=lead.matched_trainer_id,
        matched_trainer_name=tr.display_name if tr else None,
        created_at=lead.created_at,
    )


# ---------------------------------------------------------------------------
# 待售宠物
# ---------------------------------------------------------------------------


@router.get("/listings", response_model=list[ListingOut])
async def list_listings(
    user: User = Depends(get_current_user),
    species: str | None = Query(None),
    city: str | None = Query(None),
    keyword: str | None = Query(None),
):
    q = PetListing.filter(is_active=True)
    if species:
        q = q.filter(species=species)
    if keyword:
        q = q.filter(name__icontains=keyword)
    items = await q.prefetch_related("store").order_by("-id")
    if city:
        items = [p for p in items if p.store and (p.store.city or "").find(city) >= 0]
    return [listing_out(p) for p in items]


@router.get("/listings/{listing_id}", response_model=ListingOut)
async def get_listing(listing_id: int, user: User = Depends(get_current_user)):
    p = await PetListing.get_or_none(id=listing_id, is_active=True)
    if not p:
        raise HTTPException(status_code=404, detail="该宠物已下架或不存在")
    await p.fetch_related("store")
    return listing_out(p)


@router.get("/workspace/listings", response_model=list[ListingOut])
async def store_listings(user: User = Depends(get_current_user)):
    if user.role != "staff" or not user.store_id:
        raise HTTPException(status_code=403, detail="需要门店店员身份")
    items = await PetListing.filter(store_id=user.store_id).prefetch_related("store").order_by("-id")
    return [listing_out(p) for p in items]


@router.post("/workspace/listings", response_model=ListingOut)
async def create_listing(data: ListingIn, user: User = Depends(get_current_user)):
    if user.role != "staff" or not user.store_id:
        raise HTTPException(status_code=403, detail="需要门店店员身份")
    p = await PetListing.create(
        store_id=user.store_id,
        name=data.name,
        species=data.species,
        breed=data.breed,
        gender=data.gender,
        age_months=data.age_months,
        price=Decimal(str(data.price)) if data.price is not None else None,
        health_note=data.health_note,
        vaccine_note=data.vaccine_note,
        description=data.description,
        is_active=data.is_active,
        appearance=data.appearance or "standard",
        color=data.color,
        weight_kg=data.weight_kg,
        image_url=data.image_url,
    )
    await p.fetch_related("store")
    return listing_out(p)


@router.delete("/workspace/listings/{listing_id}")
async def delete_listing(listing_id: int, user: User = Depends(get_current_user)):
    if user.role != "staff" or not user.store_id:
        raise HTTPException(status_code=403, detail="需要门店店员身份")
    p = await PetListing.get_or_none(id=listing_id, store_id=user.store_id)
    if not p:
        raise HTTPException(status_code=404, detail="条目不存在")
    await p.delete()
    return {"detail": "已删除"}


# ---------------------------------------------------------------------------
# 训犬师
# ---------------------------------------------------------------------------


@router.get("/trainers", response_model=list[TrainerOut])
async def list_trainers(
    user: User = Depends(get_current_user),
    city: str | None = Query(None),
    keyword: str | None = Query(None),
    verified_only: bool = Query(True),
):
    q = TrainerProfile.all()
    if verified_only and user.role not in ("admin", "operator"):
        q = q.filter(verified=True)
    if city:
        q = q.filter(city__icontains=city)
    if keyword:
        q = q.filter(specialties__icontains=keyword)
    return [trainer_out(t) for t in await q.order_by("-verified", "-id")]


@router.get("/trainers/me", response_model=TrainerOut | None)
async def my_trainer(user: User = Depends(get_current_user)):
    t = await TrainerProfile.get_or_none(user=user)
    return trainer_out(t) if t else None


@router.post("/trainers/me", response_model=TrainerOut)
async def upsert_trainer(data: TrainerIn, user: User = Depends(get_current_user)):
    if user.role not in ("trainer", "admin"):
        raise HTTPException(status_code=403, detail="请使用训犬师账号维护主页")
    t = await TrainerProfile.get_or_none(user=user)
    payload = dict(
        display_name=data.display_name,
        city=data.city,
        specialties=data.specialties,
        years=data.years,
        price_from=Decimal(str(data.price_from)) if data.price_from is not None else None,
        service_mode=data.service_mode,
        bio=data.bio,
        avatar_url=data.avatar_url,
        experience=data.experience or "",
        cert_note=data.cert_note or "",
        proof_images=_dump_proof_images(data.proof_images),
    )
    if t:
        for k, v in payload.items():
            setattr(t, k, v)
        await t.save()
    else:
        t = await TrainerProfile.create(user=user, **payload, verified=user.role == "admin")
    return trainer_out(t)


@router.post("/trainers/{trainer_id}/verify")
async def verify_trainer(trainer_id: int, user: User = Depends(get_current_user)):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    t = await TrainerProfile.get_or_none(id=trainer_id)
    if not t:
        raise HTTPException(status_code=404, detail="训犬师不存在")
    t.verified = True
    await t.save(update_fields=["verified"])
    return {"detail": "已通过审核"}


# ---------------------------------------------------------------------------
# 需求线索（运营者工作台）
# ---------------------------------------------------------------------------


@router.get("/leads", response_model=list[LeadOut])
async def list_leads(user: User = Depends(get_current_user)):
    if user.role in ("admin", "operator"):
        rows = await Lead.all().order_by("-id")
    else:
        rows = await Lead.filter(user=user).order_by("-id")
    return [await lead_out(x) for x in rows]


@router.post("/leads", response_model=LeadOut)
async def create_lead(data: LeadIn, user: User = Depends(get_current_user)):
    if data.need_type not in NEED_TYPES:
        raise HTTPException(status_code=400, detail="未知需求类型")
    lead = await Lead.create(
        user=user,
        need_type=data.need_type,
        summary=data.summary,
        city=data.city,
        budget=data.budget,
    )
    return await lead_out(lead)


@router.post("/leads/{lead_id}/claim", response_model=LeadOut)
async def claim_lead(lead_id: int, user: User = Depends(get_current_user)):
    if user.role not in ("admin", "operator"):
        raise HTTPException(status_code=403, detail="需要运营者身份")
    lead = await Lead.get_or_none(id=lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="线索不存在")
    if lead.status != "open":
        raise HTTPException(status_code=400, detail="该线索已被领取")
    lead.operator = user
    lead.status = "claimed"
    await lead.save()
    return await lead_out(lead)


@router.post("/leads/{lead_id}/match", response_model=LeadOut)
async def match_lead(lead_id: int, data: LeadMatchIn, user: User = Depends(get_current_user)):
    if user.role not in ("admin", "operator"):
        raise HTTPException(status_code=403, detail="需要运营者身份")
    lead = await Lead.get_or_none(id=lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="线索不存在")
    if data.store_id:
        store = await Store.get_or_none(id=data.store_id)
        if not store:
            raise HTTPException(status_code=400, detail="门店不存在")
        lead.matched_store = store
    if data.trainer_id:
        tr = await TrainerProfile.get_or_none(id=data.trainer_id)
        if not tr:
            raise HTTPException(status_code=400, detail="训犬师不存在")
        lead.matched_trainer = tr
    lead.status = "matched"
    if lead.operator_id is None:
        lead.operator = user
    await lead.save()
    return await lead_out(lead)


# ---------------------------------------------------------------------------
# AI 匹配（供智能体调用）
# ---------------------------------------------------------------------------


async def match_resources(
    need_type: str | None = None,
    species: str | None = None,
    breed: str | None = None,
    city: str | None = None,
    budget: float | None = None,
    keyword: str | None = None,
) -> dict:
    """按需求类型匹配门店/待售宠物/训犬师/医院。"""
    nt = need_type or "consult"
    result: dict = {"need_type": nt, "listings": [], "stores": [], "trainers": [], "hospitals": []}

    if nt in ("buy_pet", "consult"):
        q = PetListing.filter(is_active=True)
        if species:
            q = q.filter(species=species)
        if breed:
            q = q.filter(breed__icontains=breed)
        listings = await q.prefetch_related("store").order_by("-id").limit(8)
        for p in listings:
            if city and p.store and p.store.city and city not in (p.store.city or ""):
                continue
            if budget is not None and p.price is not None and float(p.price) > budget:
                continue
            result["listings"].append(
                {
                    "id": p.id,
                    "name": p.name,
                    "species": p.species,
                    "breed": p.breed,
                    "age_months": p.age_months,
                    "appearance": getattr(p, "appearance", None),
                    "color": getattr(p, "color", None),
                    "weight_kg": getattr(p, "weight_kg", None),
                    "image_url": getattr(p, "image_url", None),
                    "price": float(p.price) if p.price is not None else None,
                    "vaccine_note": p.vaccine_note,
                    "health_note": p.health_note,
                    "store_name": p.store.name if p.store else None,
                    "store_phone": p.store.phone if p.store else None,
                    "store_address": p.store.address if p.store else None,
                    "store_city": p.store.city if p.store else None,
                    "rating": p.store.rating if p.store else None,
                }
            )

    store_type = None
    if nt == "hospital":
        store_type = "hospital"
    elif nt == "boarding":
        store_type = "boarding"
    elif nt in ("buy_pet", "product", "consult"):
        store_type = "shop"
    if store_type:
        sq = Store.filter(store_type=store_type)
        if city:
            sq = sq.filter(city__icontains=city)
        stores = await sq.order_by("-rating").limit(8)
        key = "hospitals" if store_type == "hospital" else "stores"
        for s in stores:
            result[key].append(
                {
                    "id": s.id,
                    "name": s.name,
                    "type": s.store_type,
                    "city": s.city,
                    "address": s.address,
                    "phone": s.phone,
                    "rating": s.rating,
                    "description": s.description[:120] if s.description else "",
                }
            )

    if nt in ("train", "consult"):
        tq = TrainerProfile.filter(verified=True)
        if city:
            tq = tq.filter(city__icontains=city)
        if keyword:
            tq = tq.filter(specialties__icontains=keyword)
        elif breed:
            tq = tq.filter(specialties__icontains=breed)
        trainers = await tq.order_by("-id").limit(8)
        for t in trainers:
            result["trainers"].append(
                {
                    "id": t.id,
                    "name": t.display_name,
                    "city": t.city,
                    "specialties": t.specialties,
                    "years": t.years,
                    "price_from": float(t.price_from) if t.price_from is not None else None,
                    "service_mode": t.service_mode,
                    "bio": (t.bio or "")[:120],
                }
            )

    result["note"] = "以上为平台合作资源，请引导用户到店/预约/联系训犬师。高风险健康问题必须建议就医，平台不做诊断。"
    return result


async def create_lead_for_user(user: User, need_type: str, summary: str, city=None, budget=None) -> dict:
    nt = need_type if need_type in NEED_TYPES else "consult"
    lead = await Lead.create(user=user, need_type=nt, summary=summary, city=city, budget=budget)
    return {
        "lead_id": lead.id,
        "status": lead.status,
        "need_type": lead.need_type,
        "note": "已为运营者创建需求线索，稍后会有服务商对接。",
    }
