from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from tortoise.exceptions import DoesNotExist

from app.core.config import get_settings
from app.core.security import (
    check_password_strength,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.models import User
from app.schemas.schemas import ChangePassword, Token, UserCreate, UserIn, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
settings = get_settings()

# 目标路由别名：满足对外 /register /login /users/me 的 RESTful 约定
router_alias = APIRouter(prefix="", tags=["auth"])


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效或过期的凭证")
    user_id = payload.get("user_id") or payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的凭证")
    try:
        return await User.get(id=int(user_id))
    except DoesNotExist:
        raise HTTPException(status_code=401, detail="用户不存在")


@router.post("/register", response_model=UserOut)
@router_alias.post("/register", response_model=UserOut)
async def register(data: UserCreate):
    # 超管账号由系统初始化，禁止通过注册抢占
    if data.username == settings.SUPER_ADMIN_USERNAME:
        raise HTTPException(status_code=400, detail="该用户名不可注册")
    self_roles = {"user", "operator", "trainer"}
    role = data.role if data.role in self_roles else "user"
    # 密码强度校验：不允许弱密码随便注册
    pwd_err = check_password_strength(data.password)
    if pwd_err:
        raise HTTPException(status_code=400, detail=pwd_err)
    exists = await User.filter(username=data.username).first()
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")
    if data.email:
        dup_email = await User.filter(email=data.email).first()
        if dup_email:
            raise HTTPException(status_code=400, detail="邮箱已被使用")
    user = await User.create(
        username=data.username,
        email=data.email or None,
        hashed_password=hash_password(data.password),
        role=role,
    )
    return user


@router.post("/login", response_model=Token)
@router_alias.post("/login", response_model=Token)
async def login(data: UserIn):
    user = await User.filter(username=data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(user.id, username=user.username)
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
@router_alias.get("/users/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    from app.models.models import Store

    store_type = None
    if user.store_id:
        st = await Store.get_or_none(id=user.store_id)
        store_type = st.store_type if st else None
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        store_id=user.store_id,
        staff_role=user.staff_role,
        store_type=store_type,
        points=user.points or 0,
        created_at=user.created_at,
    )


@router.post("/change-password")
@router_alias.post("/change-password")
async def change_password(
    data: ChangePassword, user: User = Depends(get_current_user)
):
    # 1. 校验旧密码
    if not verify_password(data.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="旧密码不正确")
    # 2. 新密码强度校验
    pwd_err = check_password_strength(data.new_password)
    if pwd_err:
        raise HTTPException(status_code=400, detail=pwd_err)
    # 3. 新密码不得与旧密码相同（避免无效修改）
    if data.old_password == data.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")
    # 4. 更新
    user.hashed_password = hash_password(data.new_password)
    await user.save(update_fields=["hashed_password"])
    return {"detail": "密码已修改"}