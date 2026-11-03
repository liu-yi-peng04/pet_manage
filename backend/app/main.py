from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise

from app.api import auth, booking, chat, documents, health, knowledge_base, pets, store, workspace
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.api.auth import router_alias as auth_alias_router
from app.api.knowledge_base import router as kb_router
from app.api.documents import router as doc_router
from app.api.documents import doc_router_indep
from app.api.pets import router as pets_router
from app.api.health import router as health_router
from app.api.store import router as store_router
from app.api.booking import router as booking_router
from app.api.workspace import router as workspace_router
from app.api.marketplace import router as marketplace_router
from app.api.orders import router as orders_router
from app.api.media import router as media_router
from app.core.legacy_schema import apply_legacy_column_guards, assert_aerich_baseline
from app.core.runtime_config import (
    assert_production_admin_password,
    demo_admin_password,
    demo_user_password,
    is_demo_mode,
)
from app.core.config import get_settings
from app.core.tortoise_config import CORS_ORIGINS, TORTOISE_ORM

# tortoise_config 导入时已按环境补齐演示默认值，或在生产配置非法时直接失败
settings = get_settings()


async def ensure_admin():
    """确保超管存在。生产环境不使用演示口令，也不覆盖已有密码。"""
    from app.core.security import hash_password
    from app.models.models import User

    admin_name = settings.SUPER_ADMIN_USERNAME
    admin = await User.filter(username=admin_name).first()
    if is_demo_mode(settings):
        if admin:
            if admin.role != "admin":
                admin.role = "admin"
                await admin.save(update_fields=["role"])
        else:
            admin = await User.create(
                username=admin_name,
                email=f"{admin_name}@local",
                hashed_password=hash_password(demo_admin_password(settings)),
                role="admin",
            )
            print(f"[bootstrap] 演示模式已创建超管 {admin_name}（口令未写入日志）")
        return admin

    if admin:
        if admin.role != "admin":
            admin.role = "admin"
            await admin.save(update_fields=["role"])
        return admin

    assert_production_admin_password(settings.SUPER_ADMIN_PASSWORD)
    admin = await User.create(
        username=admin_name,
        email=f"{admin_name}@local",
        hashed_password=hash_password(settings.SUPER_ADMIN_PASSWORD),
        role="admin",
    )
    print(f"[bootstrap] 已按环境变量创建超管 {admin_name}")
    return admin


async def bootstrap():
    """启动初始化: 确保超管账号存在并具备 admin 角色，创建系统公共知识库。"""
    from app.models.models import KnowledgeBase

    admin = await ensure_admin()

    # 2. 系统公共知识库（owner = 超管）
    public_kb = await KnowledgeBase.filter(name=settings.PUBLIC_KB_NAME, is_public=True).first()
    if not public_kb:
        await KnowledgeBase.create(
            name=settings.PUBLIC_KB_NAME,
            description="公司公共文档知识库，所有用户可见，仅管理员可管理。",
            owner=admin,
            is_public=True,
        )
        print(f"[bootstrap] 已创建公共知识库: {settings.PUBLIC_KB_NAME}")

    if is_demo_mode(settings):
        await _seed_demo()
    else:
        print("[bootstrap] 生产模式：跳过演示种子与演示口令重置")


async def _seed_demo():
    """补齐演示资源：城市、待售宠物、训犬师，避免空平台。仅演示模式调用。"""
    from app.core.security import hash_password
    from app.models.models import PetListing, Store, TrainerProfile, User

    demo_pwd = hash_password(demo_user_password(settings))

    stores = await Store.all()
    if stores and not stores[0].city:
        for s in stores:
            if not s.city:
                s.city = "上海"
                await s.save(update_fields=["city"])

    if not await Store.filter(store_type="hospital").exists():
        await Store.create(
            name="爱宠动物医院（合作）",
            store_type="hospital",
            city="上海",
            phone="021-58880000",
            address="示范路 88 号",
            rating=4.8,
            description="平台合作医院，可预约疫苗与就诊。",
        )
        stores = await Store.all()

    if stores and await PetListing.all().count() == 0:
        a = stores[0]
        await PetListing.create(
            store=a,
            name="金毛幼犬·豆豆",
            species="dog",
            breed="金毛寻回犬",
            gender="male",
            age_months=3,
            price=3800,
            appearance="premium",
            color="金黄",
            weight_kg=6.2,
            image_url="https://images.unsplash.com/photo-1552053831-71594a27632d?w=800&q=80",
            health_note="已驱虫，精神好",
            vaccine_note="已完成首免",
            description="适合有院子或每日能出门遛狗的家庭。",
        )
        if len(stores) > 1:
            await PetListing.create(
                store=stores[1],
                name="英短蓝猫",
                species="cat",
                breed="英国短毛猫",
                gender="female",
                age_months=4,
                price=2800,
                appearance="standard",
                color="蓝灰",
                weight_kg=2.4,
                image_url="https://images.unsplash.com/photo-1574158622682-e40e69881006?w=800&q=80",
                health_note="体内外驱虫完成",
                vaccine_note="猫三联进行中",
                description="性格稳，适合上班族。",
            )

    # 为已有待售宠物补照片，并补齐演示条目
    DEMO_PHOTOS = {
        "金毛": "https://images.unsplash.com/photo-1552053831-71594a27632d?w=800&q=80",
        "英短": "https://images.unsplash.com/photo-1574158622682-e40e69881006?w=800&q=80",
        "柯基": "https://images.unsplash.com/photo-1548199973-03cce0bbc87b?w=800&q=80",
        "哈士奇": "https://images.unsplash.com/photo-1605568427561-40dd23c2acea?w=800&q=80",
        "比熊": "https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=800&q=80",
        "橘猫": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=800&q=80",
        "布偶": "https://images.unsplash.com/photo-1596854407944-bf87f6fdd49e?w=800&q=80",
        "边牧": "https://images.unsplash.com/photo-1505628346881-b72b27e84530?w=800&q=80",
    }
    for p in await PetListing.all():
        if p.image_url:
            continue
        url = None
        text = f"{p.name}{p.breed or ''}"
        for key, photo in DEMO_PHOTOS.items():
            if key in text:
                url = photo
                break
        if not url:
            url = (
                DEMO_PHOTOS["英短"]
                if p.species == "cat"
                else DEMO_PHOTOS["金毛"]
            )
        p.image_url = url
        await p.save(update_fields=["image_url"])

    shop_stores = [s for s in stores if s.store_type in ("shop", "supplier") or not s.store_type]
    if shop_stores and await PetListing.all().count() < 6:
        extras = [
            {
                "name": "柯基·布丁",
                "species": "dog",
                "breed": "威尔士柯基",
                "gender": "female",
                "age_months": 5,
                "price": 4500,
                "appearance": "premium",
                "color": "三色",
                "weight_kg": 5.5,
                "image_url": "https://images.unsplash.com/photo-1548199973-03cce0bbc87b?w=800&q=80",
                "health_note": "体检合格",
                "vaccine_note": "已完成二免",
                "description": "腿短身长，活泼亲人，适合公寓饲养。",
            },
            {
                "name": "哈士奇·灰灰",
                "species": "dog",
                "breed": "西伯利亚雪橇犬",
                "gender": "male",
                "age_months": 8,
                "price": 3200,
                "appearance": "standard",
                "color": "灰白",
                "weight_kg": 16.0,
                "image_url": "https://images.unsplash.com/photo-1605568427561-40dd23c2acea?w=800&q=80",
                "health_note": "精力旺盛",
                "vaccine_note": "疫苗齐全",
                "description": "需要每日大量运动，适合有经验的养宠家庭。",
            },
            {
                "name": "橘猫·大橘",
                "species": "cat",
                "breed": "中华田园猫",
                "gender": "male",
                "age_months": 10,
                "price": 800,
                "appearance": "fair",
                "color": "橘白",
                "weight_kg": 4.1,
                "image_url": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=800&q=80",
                "health_note": "已绝育",
                "vaccine_note": "猫三联完成",
                "description": "粘人、饭量大，适合想养陪伴型猫咪的家庭。",
            },
            {
                "name": "布偶·奶油",
                "species": "cat",
                "breed": "布偶猫",
                "gender": "female",
                "age_months": 6,
                "price": 6800,
                "appearance": "premium",
                "color": "重点色",
                "weight_kg": 3.2,
                "image_url": "https://images.unsplash.com/photo-1596854407944-bf87f6fdd49e?w=800&q=80",
                "health_note": "血统证书可查",
                "vaccine_note": "疫苗驱虫齐全",
                "description": "性格温顺，适合有孩子的家庭。",
            },
        ]
        existing_names = {p.name for p in await PetListing.all()}
        for i, item in enumerate(extras):
            if item["name"] in existing_names:
                # 修复已知失效外链
                row = await PetListing.filter(name=item["name"]).first()
                if row and row.image_url and "photo-1495366691023" in (row.image_url or ""):
                    row.image_url = item["image_url"]
                    await row.save(update_fields=["image_url"])
                continue
            store = shop_stores[i % len(shop_stores)]
            await PetListing.create(store=store, **item)
    from app.models.models import Product

    foods = await Product.filter(category="food")
    for p in foods:
        if not getattr(p, "brand", None):
            p.brand = p.brand or "品牌待完善"
            if not p.package_spec:
                p.package_spec = "10kg"
            await p.save()

    if await TrainerProfile.all().count() == 0:
        tuser = await User.filter(username="trainer_demo").first()
        if not tuser:
            tuser = await User.create(
                username="trainer_demo",
                email="trainer@local",
                hashed_password=demo_pwd,
                role="trainer",
            )
        await TrainerProfile.create(
            user=tuser,
            display_name="林教练",
            city="上海",
            specialties="拆家,乱叫,服从训练,金毛,边牧",
            years=6,
            price_from=300,
            service_mode="both",
            bio="上门/场地训练，幼犬社会化与基础服从。",
            experience=(
                "2018-2020 宠物门店助教，负责幼犬社会化课程\n"
                "2020-2023 独立上门训犬，累计个案 200+\n"
                "2023至今 专注行为矫正与服从巩固，服务上海主城区"
            ),
            cert_note="CPDT-KA 犬类训练师认证；市民犬文明养犬指导员",
            proof_images="[]",
            verified=True,
        )

    # 固定演示身份。口令只在演示模式解析，生产路径到不了这里。
    shop = await Store.filter(store_type="shop").first()
    hospital = await Store.filter(store_type="hospital").first()
    for uname, role, extra in [
        ("demo_user", "user", {}),
        ("storeA_mgr", "staff", {"staff_role": "manager", "store_id": shop.id if shop else None}),
        ("storeA_staff", "staff", {"staff_role": "assistant", "store_id": shop.id if shop else None}),
        # 医院端：一人管一家，不设职工层级（staff_role 固定 manager）
        (
            "hospital_mgr",
            "staff",
            {"staff_role": "manager", "store_id": hospital.id if hospital else None},
        ),
        ("trainer_demo", "trainer", {}),
    ]:
        u = await User.filter(username=uname).first()
        if not u:
            await User.create(
                username=uname,
                email=f"{uname}@demo.local",
                hashed_password=demo_pwd,
                role=role,
                **{k: v for k, v in extra.items() if v is not None},
            )
        else:
            u.role = role
            u.hashed_password = demo_pwd
            for k, v in extra.items():
                if v is not None:
                    setattr(u, k, v)
            await u.save()

    # 已有 storeB_mgr：若未绑店则挂到带「B」的医院或首家医院，作为医院端账号
    b = await User.filter(username="storeB_mgr").first()
    if b:
        b_hosp = await Store.filter(store_type="hospital", name__contains="B").first()
        target = b_hosp or hospital
        if target and not b.store_id:
            b.role = "staff"
            b.staff_role = "manager"
            b.store_id = target.id
            b.hashed_password = demo_pwd
            await b.save()
        elif b.store_id:
            # 已绑定则仅保证密码与角色可用
            b.role = "staff"
            b.staff_role = "manager"
            b.hashed_password = demo_pwd
            await b.save()

    # 已有演示训犬师若经历为空则补文案，不覆盖后台改过的内容
    try:
        demo_t = await TrainerProfile.filter(display_name="林教练").first()
        if demo_t and not (demo_t.experience or "").strip():
            demo_t.experience = (
                "2018-2020 宠物门店助教，负责幼犬社会化课程\n"
                "2020-2023 独立上门训犬，累计个案 200+\n"
                "2023至今 专注行为矫正与服从巩固，服务上海主城区"
            )
            demo_t.cert_note = demo_t.cert_note or "CPDT-KA 犬类训练师认证；市民犬文明养犬指导员"
            await demo_t.save(update_fields=["experience", "cert_note"])
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    from tortoise import connections

    await Tortoise.init(config=TORTOISE_ORM)
    if is_demo_mode(settings):
        # 演示库可能尚未跑过 aerich。safe 建表只补缺失表，不删数据。
        if settings.DEMO_AUTO_SCHEMA:
            await Tortoise.generate_schemas()
            await apply_legacy_column_guards(connections.get("default"))
            print("[bootstrap] 演示模式已执行 generate_schemas 与缺列补丁")
        else:
            print("[bootstrap] 演示模式已关闭自动建表，假定结构由 aerich 维护")
    else:
        # 生产环境禁止启动期 DDL。表结构以 migrations 为准。
        await assert_aerich_baseline(connections.get("default"))
    await bootstrap()
    yield
    await Tortoise.close_connections()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(auth_alias_router)
app.include_router(kb_router)
app.include_router(doc_router)
app.include_router(doc_router_indep)
app.include_router(chat_router)
app.include_router(pets_router)
app.include_router(health_router)
app.include_router(store_router)
app.include_router(booking_router)
app.include_router(workspace_router)
app.include_router(marketplace_router)
app.include_router(orders_router)
app.include_router(media_router)


@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "status": "ok"}