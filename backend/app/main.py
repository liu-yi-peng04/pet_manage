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
from app.core.config import get_settings

settings = get_settings()

TORTOISE_CONFIG = {
    "connections": {"default": settings.DATABASE_URL},
    "apps": {"models": {"models": ["app.models.models"], "default_connection": "default"}},
}


async def bootstrap():
    """启动初始化: 确保超管账号存在并具备 admin 角色，创建系统公共知识库。"""
    from app.core.security import hash_password
    from app.models.models import KnowledgeBase, User
    from tortoise import connections

    # 兼容旧库：会话端隔离字段；预约表训犬师外键
    try:
        conn = connections.get("default")
        await conn.execute_query(
            "ALTER TABLE conversation ADD COLUMN channel VARCHAR(32) NOT NULL DEFAULT 'user'"
        )
    except Exception:
        pass
    try:
        conn = connections.get("default")
        await conn.execute_query(
            "ALTER TABLE appointment ADD COLUMN trainer_id INT NULL"
        )
    except Exception:
        pass
    # 训犬师信任材料字段
    for sql in (
        "ALTER TABLE trainerprofile ADD COLUMN avatar_url VARCHAR(500) NULL",
        "ALTER TABLE trainerprofile ADD COLUMN experience LONGTEXT NULL",
        "ALTER TABLE trainerprofile ADD COLUMN cert_note LONGTEXT NULL",
        "ALTER TABLE trainerprofile ADD COLUMN proof_images LONGTEXT NULL",
    ):
        try:
            conn = connections.get("default")
            await conn.execute_query(sql)
        except Exception:
            pass
    try:
        conn = connections.get("default")
        await conn.execute_query(
            "UPDATE trainerprofile SET experience=COALESCE(experience,'')"
        )
        await conn.execute_query(
            "UPDATE trainerprofile SET cert_note=COALESCE(cert_note,'')"
        )
        await conn.execute_query(
            "UPDATE trainerprofile SET proof_images=COALESCE(NULLIF(proof_images,''),'[]')"
        )
    except Exception:
        pass

    # 演示训犬师补齐经历文案（仅空时写入，不覆盖已编辑内容）
    try:
        from app.models.models import TrainerProfile as TP

        demo_t = await TP.filter(display_name="林教练").first()
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

    # 1. 超管账号
    admin_name = settings.SUPER_ADMIN_USERNAME
    admin = await User.filter(username=admin_name).first()
    if admin:
        if admin.role != "admin":
            admin.role = "admin"
            await admin.save(update_fields=["role"])
    else:
        admin = await User.create(
            username=admin_name,
            email=f"{admin_name}@local",
            hashed_password=hash_password("admin123"),
            role="admin",
        )
        print(f"[bootstrap] 已自动创建超管账号: {admin_name} / admin123（请尽快修改密码）")

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

    await _seed_demo()


async def _seed_demo():
    """补齐演示资源：城市、待售宠物、训犬师，避免空平台。"""
    from app.core.security import hash_password
    from app.models.models import PetListing, Store, TrainerProfile, User

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
                hashed_password=hash_password("Passw0rd!a"),
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

    # 固定演示身份（密码 Passw0rd!a）
    shop = await Store.filter(store_type="shop").first()
    hospital = await Store.filter(store_type="hospital").first()
    demo_pwd = hash_password("Passw0rd!a")
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await Tortoise.init(config=TORTOISE_CONFIG)
    await Tortoise.generate_schemas()
    await bootstrap()
    yield
    await Tortoise.close_connections()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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