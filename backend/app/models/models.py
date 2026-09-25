from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=64, unique=True)
    email = fields.CharField(max_length=128, null=True, unique=True)
    hashed_password = fields.CharField(max_length=255)
    # role: user(养宠用户) / admin / staff(门店) / operator(服务运营者) / trainer(训犬师)
    role = fields.CharField(max_length=20, default="user")
    # staff 归属门店；非 staff 时为 None
    store = fields.ForeignKeyField("models.Store", related_name="staff", null=True)
    # staff_role: manager(店主) / assistant(店员)
    staff_role = fields.CharField(max_length=20, null=True)
    points = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)

    knowledge_bases: fields.ReverseRelation["KnowledgeBase"]
    conversations: fields.ReverseRelation["Conversation"]


class KnowledgeBase(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=128)
    description = fields.TextField(default="")
    owner = fields.ForeignKeyField("models.User", related_name="knowledge_bases")
    # 是否为公共知识库；公共库对所有用户只读可见，仅 admin 可管理文档
    is_public = fields.BooleanField(default=False)
    # 门店内容库：绑定门店后本店 staff 可管理；None 表示个人/历史库
    store = fields.ForeignKeyField("models.Store", related_name="knowledge_bases", null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    documents: fields.ReverseRelation["Document"]


class Document(Model):
    id = fields.IntField(pk=True)
    kb = fields.ForeignKeyField("models.KnowledgeBase", related_name="documents")
    filename = fields.CharField(max_length=255)
    file_path = fields.CharField(max_length=500)
    file_type = fields.CharField(max_length=20, default="txt")
    # status: pending / indexed
    status = fields.CharField(max_length=20, default="pending")
    created_at = fields.DatetimeField(auto_now_add=True)


class Conversation(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="conversations")
    kb = fields.ForeignKeyField("models.KnowledgeBase", related_name="conversations", null=True)
    title = fields.CharField(max_length=255, default="新对话")
    # 端隔离：user / staff / admin / operator / trainer，互不可见
    channel = fields.CharField(max_length=32, default="user")
    created_at = fields.DatetimeField(auto_now_add=True)

    messages: fields.ReverseRelation["ChatMessage"]


class ChatMessage(Model):
    id = fields.IntField(pk=True)
    conversation = fields.ForeignKeyField("models.Conversation", related_name="messages")
    role = fields.CharField(max_length=20)  # user / assistant
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)


class MediaAsset(Model):
    """上传的图片以 Base64 文本存入数据库，通过 /api/media/{id} 读取。"""

    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="media_assets", null=True)
    # purpose: pet / listing / product / other
    purpose = fields.CharField(max_length=20, default="other")
    filename = fields.CharField(max_length=255)
    content_type = fields.CharField(max_length=64, default="image/jpeg")
    size = fields.IntField(default=0)
    # 图片二进制转 Base64 后存 LONGTEXT，便于备份与跨端读取
    data_b64 = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "media_asset"


class Pet(Model):
    """宠物档案：主人手动录入，AI 管家只读查询。"""

    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="pets")
    name = fields.CharField(max_length=64)
    # species: dog / cat / other
    species = fields.CharField(max_length=20, default="dog")
    breed = fields.CharField(max_length=64, null=True)
    # gender: male / female
    gender = fields.CharField(max_length=10, default="unknown")
    birth_date = fields.DateField(null=True)
    weight_kg = fields.FloatField(null=True)
    chip_no = fields.CharField(max_length=64, null=True)
    is_neutered = fields.BooleanField(default=False)
    # 同名宠物用昵称区分，如「大旺财」
    nickname = fields.CharField(max_length=64, default="")
    color = fields.CharField(max_length=64, null=True)
    # activity_level: low / medium / high
    activity_level = fields.CharField(max_length=20, default="medium")
    diet = fields.TextField(default="")
    allergies = fields.TextField(default="")
    chronic_conditions = fields.TextField(default="")
    temperament = fields.CharField(max_length=128, null=True)
    # living_env: indoor / outdoor / mixed / apartment
    living_env = fields.CharField(max_length=32, default="indoor")
    city = fields.CharField(max_length=64, null=True)
    notes = fields.TextField(default="")
    # 宠物照片：/api/media/{id} 或外链
    image_url = fields.CharField(max_length=500, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    vaccines: fields.ReverseRelation["VaccineRecord"]
    exams: fields.ReverseRelation["MedicalExam"]
    medications: fields.ReverseRelation["MedicationRecord"]


class VaccineRecord(Model):
    """疫苗记录：主人手动录入，next_due_date 用于到期提醒。"""

    id = fields.IntField(pk=True)
    pet = fields.ForeignKeyField("models.Pet", related_name="vaccines")
    vaccine_name = fields.CharField(max_length=64)
    dose_no = fields.IntField(default=1)
    vaccinated_at = fields.DateField()
    next_due_date = fields.DateField(null=True)
    notes = fields.TextField(default="")
    created_at = fields.DatetimeField(auto_now_add=True)


class MedicalExam(Model):
    """体检记录：可空展示「未做体检」。"""

    id = fields.IntField(pk=True)
    pet = fields.ForeignKeyField("models.Pet", related_name="exams")
    exam_date = fields.DateField()
    hospital = fields.CharField(max_length=128, null=True)
    # 体检项目（逗号分隔或文本）：血常规/生化/B超等
    items = fields.CharField(max_length=255, null=True)
    result = fields.TextField(default="")
    vet_name = fields.CharField(max_length=64, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class MedicationRecord(Model):
    """用药记录：可空展示「未使用药物」。"""

    id = fields.IntField(pk=True)
    pet = fields.ForeignKeyField("models.Pet", related_name="medications")
    drug_name = fields.CharField(max_length=128)
    start_date = fields.DateField(null=True)
    end_date = fields.DateField(null=True)
    dosage = fields.CharField(max_length=128, null=True)
    reason = fields.CharField(max_length=255, null=True)
    notes = fields.TextField(default="")
    created_at = fields.DatetimeField(auto_now_add=True)


class Store(Model):
    """合作商家：宠物店 / 医院 / 寄养中心 / 用品供应商。"""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=128)
    # store_type: shop / hospital / boarding / supplier
    store_type = fields.CharField(max_length=20, default="shop")
    address = fields.CharField(max_length=255, null=True)
    phone = fields.CharField(max_length=32, null=True)
    city = fields.CharField(max_length=64, null=True)
    rating = fields.FloatField(default=5.0)
    description = fields.TextField(default="")
    created_at = fields.DatetimeField(auto_now_add=True)

    products: fields.ReverseRelation["Product"]
    appointments: fields.ReverseRelation["Appointment"]
    boardings: fields.ReverseRelation["BoardingReservation"]
    staff: fields.ReverseRelation["User"]
    knowledge_bases: fields.ReverseRelation["KnowledgeBase"]


class Product(Model):
    """在售商品：支持库存、优惠与配送方式，走平台订单履约。"""

    id = fields.IntField(pk=True)
    store = fields.ForeignKeyField("models.Store", related_name="products", null=True)
    name = fields.CharField(max_length=128)
    # category: cage(笼子) / toy(玩具) / supply(用品) / food(食品) / health(医疗保健)
    category = fields.CharField(max_length=20, default="supply")
    price = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    # 适用物种: dog / cat / both
    species = fields.CharField(max_length=10, default="both")
    # 适用体重区间(kg)，用于 AI 按档案推荐规格
    min_weight_kg = fields.FloatField(null=True)
    max_weight_kg = fields.FloatField(null=True)
    spec = fields.CharField(max_length=128, null=True)
    image_url = fields.CharField(max_length=500, null=True)
    description = fields.TextField(default="")
    is_active = fields.BooleanField(default=True)
    stock = fields.IntField(default=99)
    promo = fields.CharField(max_length=128, null=True)
    # shipping_mode: instant(同城即时) / express(快递)
    shipping_mode = fields.CharField(max_length=20, default="instant")
    # 品牌与包装（狗粮等食品必填更有意义）
    brand = fields.CharField(max_length=64, null=True)
    package_spec = fields.CharField(max_length=64, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class Appointment(Model):
    """预约：门店就诊/美容/寄养咨询，或训犬师训练课时。"""

    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="appointments")
    pet = fields.ForeignKeyField("models.Pet", related_name="appointments", null=True)
    store = fields.ForeignKeyField("models.Store", related_name="appointments", null=True)
    # 训犬师预约时绑定教练主页；与 store 二选一为主
    trainer = fields.ForeignKeyField(
        "models.TrainerProfile", related_name="appointments", null=True
    )
    # appt_type: exam / grooming / boarding / consult / train
    appt_type = fields.CharField(max_length=20, default="exam")
    appt_time = fields.DatetimeField()
    # status: pending / confirmed / completed / cancelled
    status = fields.CharField(max_length=20, default="pending")
    notes = fields.TextField(default="")
    created_at = fields.DatetimeField(auto_now_add=True)


class BoardingReservation(Model):
    """寄养预订：按天排期。"""

    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="boardings")
    pet = fields.ForeignKeyField("models.Pet", related_name="boardings")
    store = fields.ForeignKeyField("models.Store", related_name="boardings", null=True)
    start_date = fields.DateField()
    end_date = fields.DateField()
    daily_fee = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    notes = fields.TextField(default="")
    # status: pending / confirmed / completed / cancelled
    status = fields.CharField(max_length=20, default="pending")
    created_at = fields.DatetimeField(auto_now_add=True)


class PetListing(Model):
    """门店待售/待领养宠物展示，供选宠匹配（非主人档案）。"""

    id = fields.IntField(pk=True)
    store = fields.ForeignKeyField("models.Store", related_name="listings")
    name = fields.CharField(max_length=64)
    species = fields.CharField(max_length=20, default="dog")
    breed = fields.CharField(max_length=64, null=True)
    gender = fields.CharField(max_length=10, default="unknown")
    age_months = fields.IntField(null=True)
    price = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    health_note = fields.CharField(max_length=255, null=True)
    vaccine_note = fields.CharField(max_length=255, null=True)
    description = fields.TextField(default="")
    # appearance: premium / standard / fair / sale
    appearance = fields.CharField(max_length=20, default="standard")
    color = fields.CharField(max_length=64, null=True)
    weight_kg = fields.FloatField(null=True)
    image_url = fields.CharField(max_length=500, null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class TrainerProfile(Model):
    """训犬师主页：平台审核后对外展示；经历与证明图用于建立信任。"""

    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="trainer_profile", unique=True)
    display_name = fields.CharField(max_length=64)
    city = fields.CharField(max_length=64, null=True)
    specialties = fields.CharField(max_length=255, default="")  # 犬种/问题类型
    years = fields.IntField(default=1)
    price_from = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    # service_mode: home / studio / both
    service_mode = fields.CharField(max_length=20, default="both")
    bio = fields.TextField(default="")
    # 头像：/api/media/{id}
    avatar_url = fields.CharField(max_length=500, null=True)
    # 从业经历履历（时间线文案）
    experience = fields.TextField(default="")
    # 证书/资质文字说明
    cert_note = fields.TextField(default="")
    # 证明图 JSON：证书照、训练前后案例等，如 ["/api/media/1","/api/media/2"]
    proof_images = fields.TextField(default="[]")
    verified = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)


class Order(Model):
    """商品订单：用户下单 → 商家履约 → 配送完成（一期无第三方支付）。"""

    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="orders")
    store = fields.ForeignKeyField("models.Store", related_name="orders")
    # status: pending / accepted / preparing / delivering / completed / cancelled
    status = fields.CharField(max_length=20, default="pending")
    shipping_mode = fields.CharField(max_length=20, default="instant")
    address = fields.CharField(max_length=255)
    total = fields.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = fields.TextField(default="")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "shop_order"


class OrderItem(Model):
    id = fields.IntField(pk=True)
    order = fields.ForeignKeyField("models.Order", related_name="items")
    product = fields.ForeignKeyField("models.Product", related_name="order_items", null=True)
    name = fields.CharField(max_length=128)
    qty = fields.IntField(default=1)
    price = fields.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        table = "shop_orderitem"


class Lead(Model):
    """用户需求线索：运营者获客与资源匹配的工作单。"""

    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="leads")
    operator = fields.ForeignKeyField("models.User", related_name="claimed_leads", null=True)
    # need_type: buy_pet / product / train / hospital / boarding / consult
    need_type = fields.CharField(max_length=20, default="consult")
    summary = fields.TextField()
    city = fields.CharField(max_length=64, null=True)
    budget = fields.FloatField(null=True)
    status = fields.CharField(max_length=20, default="open")  # open / claimed / matched / closed
    matched_store = fields.ForeignKeyField("models.Store", related_name="leads", null=True)
    matched_trainer = fields.ForeignKeyField(
        "models.TrainerProfile", related_name="leads", null=True
    )
    created_at = fields.DatetimeField(auto_now_add=True)