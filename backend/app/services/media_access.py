"""媒体读取 ACL。

未登录一律拒绝。已登录用户可以读取：
- 自己上传的文件
- 没有属主的历史数据
- 目录类用途（待售宠物、商品、训犬师资料），否则选宠/商城/训犬师页无法展示别人上传的图
宠物档案等私有用途只允许属主和管理员。
"""
from __future__ import annotations

CATALOG_PURPOSES = frozenset({"listing", "product", "trainer"})


def can_read_media(user, asset) -> bool:
    role = (getattr(user, "role", "") or "").strip().lower()
    if role == "admin":
        return True
    owner_id = getattr(asset, "owner_id", None)
    if owner_id is None or owner_id == getattr(user, "id", None):
        return True
    purpose = (getattr(asset, "purpose", "") or "").strip().lower()
    return purpose in CATALOG_PURPOSES
