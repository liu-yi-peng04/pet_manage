from datetime import date, datetime

from pydantic import BaseModel, field_validator

from app.core.security import check_email_rule, check_username_rule


class UserCreate(BaseModel):
    username: str
    email: str = ""
    password: str
    # 自助注册身份：user / operator / trainer
    role: str = "user"

    @field_validator("username")
    @classmethod
    def _check_username(cls, v: str) -> str:
        err = check_username_rule(v or "")
        if err:
            raise ValueError(err)
        return v

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: str) -> str:
        if v:
            err = check_email_rule(v)
            if err:
                raise ValueError(err)
        return v


class UserIn(BaseModel):
    username: str
    password: str


class ChangePassword(BaseModel):
    old_password: str
    new_password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str | None = None
    role: str = "user"
    store_id: int | None = None
    staff_role: str | None = None
    # 门店类型：shop / hospital / boarding（仅 staff 有意义）
    store_type: str | None = None
    points: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str = ""


class KnowledgeBaseOut(BaseModel):
    id: int
    name: str
    description: str
    is_public: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageIn(BaseModel):
    kb_id: int | None = None
    conversation_id: int | None = None
    content: str
    # C 端当前关注的宠物，供档案/疫苗/导购工具优先使用
    pet_id: int | None = None
    # pet=养宠咨询；policy=门店/公司内部制度（管理端默认）
    consult_type: str | None = None


class ChatMessageOut(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PetIn(BaseModel):
    name: str
    species: str = "dog"
    breed: str | None = None
    gender: str = "unknown"
    birth_date: str | None = None
    weight_kg: float | None = None
    chip_no: str | None = None
    is_neutered: bool = False
    nickname: str = ""
    color: str | None = None
    activity_level: str = "medium"
    diet: str = ""
    allergies: str = ""
    chronic_conditions: str = ""
    temperament: str | None = None
    living_env: str = "indoor"
    city: str | None = None
    notes: str = ""
    image_url: str | None = None


class PetOut(BaseModel):
    id: int
    name: str
    species: str
    breed: str | None = None
    gender: str
    birth_date: date | None = None
    weight_kg: float | None = None
    chip_no: str | None = None
    is_neutered: bool
    nickname: str | None = ""
    color: str | None = None
    activity_level: str | None = "medium"
    diet: str | None = ""
    allergies: str | None = ""
    chronic_conditions: str | None = ""
    temperament: str | None = None
    living_env: str | None = "indoor"
    city: str | None = None
    notes: str
    image_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MediaOut(BaseModel):
    id: int
    url: str
    filename: str
    content_type: str
    size: int
    purpose: str = "other"


class VaccineIn(BaseModel):
    vaccine_name: str
    dose_no: int = 1
    vaccinated_at: str
    next_due_date: str | None = None
    notes: str = ""


class VaccineOut(BaseModel):
    id: int
    pet_id: int
    vaccine_name: str
    dose_no: int
    vaccinated_at: date
    next_due_date: date | None = None
    notes: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MedicalExamIn(BaseModel):
    exam_date: str
    hospital: str | None = None
    items: str | None = None
    result: str = ""
    vet_name: str | None = None


class MedicalExamOut(BaseModel):
    id: int
    pet_id: int
    exam_date: date
    hospital: str | None = None
    items: str | None = None
    result: str
    vet_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MedicationIn(BaseModel):
    drug_name: str
    start_date: str | None = None
    end_date: str | None = None
    dosage: str | None = None
    reason: str | None = None
    notes: str = ""


class MedicationOut(BaseModel):
    id: int
    pet_id: int
    drug_name: str
    start_date: date | None = None
    end_date: date | None = None
    dosage: str | None = None
    reason: str | None = None
    notes: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StoreIn(BaseModel):
    name: str
    store_type: str = "shop"
    address: str | None = None
    phone: str | None = None
    city: str | None = None
    description: str = ""


class StoreOut(BaseModel):
    id: int
    name: str
    store_type: str
    address: str | None = None
    phone: str | None = None
    city: str | None = None
    rating: float = 5.0
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StaffAssignIn(BaseModel):
    """超管将某用户设为门店店员。"""
    user_id: int
    staff_role: str = "assistant"  # manager(店主) / assistant(店员)


class StaffOut(BaseModel):
    id: int
    username: str
    email: str | None = None
    staff_role: str | None = None
    store_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AppointmentStatusIn(BaseModel):
    status: str  # pending / confirmed / completed / cancelled


class BoardingStatusIn(BaseModel):
    status: str


class CustomerPetOut(BaseModel):
    id: int
    name: str
    species: str
    breed: str | None = None


class CustomerOut(BaseModel):
    id: int
    username: str
    email: str | None = None
    pets: list[CustomerPetOut] = []
    last_appointment_at: datetime | None = None


class StoreOverviewOut(BaseModel):
    store: StoreOut
    staff: int = 0
    pending_appointments: int = 0
    active_boardings: int = 0
    customers: int = 0
    products: int = 0
    due_vaccines: int = 0


class ProductIn(BaseModel):
    name: str
    store_id: int | None = None
    category: str = "supply"
    price: float | None = None
    species: str = "both"
    min_weight_kg: float | None = None
    max_weight_kg: float | None = None
    spec: str | None = None
    image_url: str | None = None
    description: str = ""
    is_active: bool = True
    stock: int = 99
    promo: str | None = None
    shipping_mode: str = "instant"
    brand: str | None = None
    package_spec: str | None = None


class ProductOut(BaseModel):
    id: int
    store_id: int | None = None
    name: str
    category: str
    price: float | None = None
    species: str
    min_weight_kg: float | None = None
    max_weight_kg: float | None = None
    spec: str | None = None
    image_url: str | None = None
    description: str
    is_active: bool
    created_at: datetime
    store_name: str | None = None
    store_phone: str | None = None
    store_address: str | None = None
    store_city: str | None = None
    store_rating: float | None = None
    stock: int = 0
    promo: str | None = None
    shipping_mode: str = "instant"
    brand: str | None = None
    package_spec: str | None = None

    model_config = {"from_attributes": True}


class VaccineRecallOut(BaseModel):
    """本店客户疫苗临期/过期，供门店召回。"""

    vaccine_id: int
    pet_id: int
    pet_name: str
    species: str
    owner_id: int
    owner_name: str
    vaccine_name: str
    dose_no: int
    next_due_date: date
    status: str  # overdue / due_soon
    days_left: int


class VaccineInviteIn(BaseModel):
    """宠物店作为中转站：代客户向合作医院预约接种（不在本店打针）。"""

    pet_id: int
    vaccine_id: int | None = None
    # 目标医院 store_id；店铺端必填
    hospital_id: int | None = None
    appt_time: str | None = None
    notes: str = ""


class AppointmentIn(BaseModel):
    pet_id: int | None = None
    store_id: int | None = None
    trainer_id: int | None = None
    appt_type: str = "exam"
    appt_time: str
    notes: str = ""


class AppointmentOut(BaseModel):
    id: int
    user_id: int
    pet_id: int | None = None
    store_id: int | None = None
    trainer_id: int | None = None
    appt_type: str
    appt_time: datetime
    status: str
    notes: str
    created_at: datetime
    store_name: str | None = None
    store_type: str | None = None
    trainer_name: str | None = None
    pet_name: str | None = None
    user_name: str | None = None

    model_config = {"from_attributes": True}


class BoardingIn(BaseModel):
    pet_id: int
    store_id: int | None = None
    start_date: str
    end_date: str
    daily_fee: float | None = None
    notes: str = ""


class BoardingOut(BaseModel):
    id: int
    user_id: int
    pet_id: int
    store_id: int | None = None
    start_date: date
    end_date: date
    daily_fee: float | None = None
    notes: str
    status: str
    created_at: datetime
    store_name: str | None = None
    pet_name: str | None = None

    model_config = {"from_attributes": True}


class ListingIn(BaseModel):
    name: str
    species: str = "dog"
    breed: str | None = None
    gender: str = "unknown"
    age_months: int | None = None
    price: float | None = None
    health_note: str | None = None
    vaccine_note: str | None = None
    description: str = ""
    is_active: bool = True
    store_id: int | None = None
    appearance: str = "standard"
    color: str | None = None
    weight_kg: float | None = None
    image_url: str | None = None


class ListingOut(BaseModel):
    id: int
    store_id: int
    store_name: str | None = None
    store_phone: str | None = None
    store_address: str | None = None
    store_city: str | None = None
    store_rating: float | None = None
    name: str
    species: str
    breed: str | None = None
    gender: str
    age_months: int | None = None
    price: float | None = None
    health_note: str | None = None
    vaccine_note: str | None = None
    description: str
    appearance: str = "standard"
    color: str | None = None
    weight_kg: float | None = None
    image_url: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainerIn(BaseModel):
    display_name: str
    city: str | None = None
    specialties: str = ""
    years: int = 1
    price_from: float | None = None
    service_mode: str = "both"
    bio: str = ""
    avatar_url: str | None = None
    experience: str = ""
    cert_note: str = ""
    proof_images: list[str] = []


class TrainerOut(BaseModel):
    id: int
    user_id: int
    display_name: str
    city: str | None = None
    specialties: str
    years: int
    price_from: float | None = None
    service_mode: str
    bio: str
    avatar_url: str | None = None
    experience: str = ""
    cert_note: str = ""
    proof_images: list[str] = []
    verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadIn(BaseModel):
    need_type: str = "consult"
    summary: str
    city: str | None = None
    budget: float | None = None


class LeadMatchIn(BaseModel):
    store_id: int | None = None
    trainer_id: int | None = None


class LeadOut(BaseModel):
    id: int
    user_id: int
    user_name: str | None = None
    operator_id: int | None = None
    need_type: str
    summary: str
    city: str | None = None
    budget: float | None = None
    status: str
    matched_store_id: int | None = None
    matched_store_name: str | None = None
    matched_trainer_id: int | None = None
    matched_trainer_name: str | None = None
    created_at: datetime


class OrderItemIn(BaseModel):
    product_id: int
    qty: int = 1


class OrderIn(BaseModel):
    items: list[OrderItemIn]
    address: str
    shipping_mode: str | None = None
    notes: str = ""


class OrderItemOut(BaseModel):
    id: int
    product_id: int | None = None
    name: str
    qty: int
    price: float


class OrderOut(BaseModel):
    id: int
    user_id: int
    store_id: int
    store_name: str | None = None
    status: str
    shipping_mode: str
    address: str
    total: float
    notes: str
    items: list[OrderItemOut] = []
    created_at: datetime


class OrderStatusIn(BaseModel):
    status: str