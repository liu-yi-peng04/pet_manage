"""旧库手工补列。常规请在 backend 目录执行 aerich upgrade，不要在应用启动时调用。

本脚本不再内置数据库口令。请先设置 DATABASE_URL。
"""
import os
from urllib.parse import unquote, urlparse

import pymysql

raw = os.environ.get("DATABASE_URL", "").strip()
if not raw:
    raise SystemExit("请设置 DATABASE_URL。本脚本不再内置演示数据库口令。")
parsed = urlparse(raw)
if parsed.scheme not in {"mysql", "mysql+aiomysql"}:
    raise SystemExit("仅支持 mysql DATABASE_URL")

conn = pymysql.connect(
    host=parsed.hostname or "127.0.0.1",
    port=parsed.port or 3306,
    user=unquote(parsed.username or ""),
    password=unquote(parsed.password or ""),
    db=(parsed.path or "/").lstrip("/"),
    charset="utf8mb4",
)
cur = conn.cursor()

def has(c):
    cur.execute("SHOW COLUMNS FROM user")
    return any(r[0] == c for r in cur.fetchall())

if not has("store_id"):
    cur.execute("ALTER TABLE user ADD COLUMN store_id INT NULL")
    print("added user.store_id")
else:
    print("user.store_id exists")

if not has("staff_role"):
    cur.execute("ALTER TABLE user ADD COLUMN staff_role VARCHAR(20) NULL")
    print("added user.staff_role")
else:
    print("user.staff_role exists")

conn.commit()
conn.close()
print("done")