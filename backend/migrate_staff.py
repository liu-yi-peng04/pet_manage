import pymysql

conn = pymysql.connect(
    host="127.0.0.1", port=3306, user="root", password="123456", db="ai_kb", charset="utf8mb4"
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