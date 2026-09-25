from datetime import datetime, timedelta, timezone
import hashlib
import os
import re

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()

# 哈希方案前缀标记：新版用 bcrypt，旧版用 pbkdf2（保留兼容）
BCRYPT_PREFIX = "$bcrypt$"


def hash_password(password: str) -> str:
    """bcrypt 加密，加前缀标记以便校验时识别方案。"""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()
    return BCRYPT_PREFIX + hashed


def verify_password(password: str, stored: str) -> bool:
    """校验密码：自动识别 bcrypt(新) 与 pbkdf2(旧) 两种存储格式。"""
    try:
        if stored.startswith(BCRYPT_PREFIX):
            raw = stored[len(BCRYPT_PREFIX):]
            return bcrypt.checkpw(password.encode("utf-8"), raw.encode("utf-8"))
        # 旧版 pbkdf2: salt_hex$digest_hex
        salt_hex, digest_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return digest.hex() == digest_hex
    except Exception:
        return False


def create_access_token(user_id: int | str, username: str | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "user_id": str(user_id),
        "sub": str(user_id),
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict | None:
    """校验并解析 token，失败或过期返回 None。"""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


WEAK_PASSWORDS = {
    "123456", "12345678", "password", "password1", "qwerty",
    "qwerty123", "admin", "admin123", "111111", "123123",
}


def check_password_strength(password: str) -> str:
    """校验密码强度，返回错误说明；通过则返回空字符串。

    规则：8-64 位；需同时含大写字、小写字、数字、特殊字符四类中的至少三类；
    不得为常见弱密码；不得连续递增/递减或连续重复。
    """
    if len(password) < 8 or len(password) > 64:
        return "密码长度需为 8-64 位"
    if password.lower() in WEAK_PASSWORDS:
        return "密码过于常见，请更换"
    types = 0
    if re.search(r"[a-z]", password):
        types += 1
    if re.search(r"[A-Z]", password):
        types += 1
    if re.search(r"[0-9]", password):
        types += 1
    if re.search(r"[^a-zA-Z0-9]", password):
        types += 1
    if types < 3:
        return "密码需包含大写字母、小写字母、数字、特殊字符中的至少三类"
    for seq in (password.lower(), password.lower()[::-1]):
        for i in range(len(seq) - 2):
            if seq[i] == seq[i + 1] == seq[i + 2]:
                return "密码不能包含连续 3 个相同字符"
    return ""


def check_username_rule(username: str) -> str:
    """校验用户名规则：3-24 位，字母开头，可含字母/数字/下划线。"""
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,23}", username):
        return "用户名需为 3-24 位，以字母开头，仅含字母/数字/下划线"
    return ""


def check_email_rule(email: str) -> str:
    """校验邮箱格式，返回错误说明；通过返回空字符串。"""
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return "邮箱格式不正确"
    return ""