import json
import urllib.request

BASE = "http://127.0.0.1:8000"


def call(method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def login(u, p):
    s, b = call("POST", "/api/auth/login", None, {"username": u, "password": p})
    return json.loads(b).get("access_token") if s == 200 else None


# ---- 准备：admin 登录、注册两个店员、两个普通用户 ----
admin = login("admin", "admin123")
for u, p in [("storeA_mgr", "Passw0rd!a"), ("storeB_mgr", "Passw0rd!a"), ("storeA_staff", "Passw0rd!a"), ("customer1", "Passw0rd!a"), ("customer2", "Passw0rd!a")]:
    s, b = call("POST", "/api/auth/register", None, {"username": u, "password": p, "email": f"{u}@t.com"})
    print("register", u, s)

# 读取用户 id
def uid(name):
    for u, _ in []:
        pass
    # 通过 admin 无法列全部用户，注册响应里带 id，这里直接查 login 后 /users/me
    return None

# 拿到各用户 id：注册返回自增，重新 login 取 /users/me
ids = {}
for u in ["storeA_mgr", "storeB_mgr", "storeA_staff", "customer1", "customer2"]:
    t = login(u, "Passw0rd!a")
    s, b = call("GET", "/users/me", t)
    ids[u] = json.loads(b)["id"]
print("ids", ids)

# ---- 建两家店 ----
s, b = call("POST", "/api/stores", admin, {"name": "A店宠物生活馆", "store_type": "shop"})
storeA = json.loads(b); print("create storeA", s, storeA["id"], storeA["name"])
s, b = call("POST", "/api/stores", admin, {"name": "B店宠物诊所", "store_type": "hospital"})
storeB = json.loads(b); print("create storeB", s, storeB["id"], storeB["name"])

# ---- 分配店员：storeA 店主+店员，storeB 店主 ----
s, b = call("POST", f"/api/stores/{storeA['id']}/staff", admin, {"user_id": ids["storeA_mgr"], "staff_role": "manager"})
print("assign storeA mgr", s)
s, b = call("POST", f"/api/stores/{storeA['id']}/staff", admin, {"user_id": ids["storeA_staff"], "staff_role": "assistant"})
print("assign storeA staff", s)
s, b = call("POST", f"/api/stores/{storeB['id']}/staff", admin, {"user_id": ids["storeB_mgr"], "staff_role": "manager"})
print("assign storeB mgr", s)

# ---- 两个普通用户各建宠物并预约到不同店 ----
t1 = login("customer1", "Passw0rd!a")
t2 = login("customer2", "Passw0rd!a")
s, b = call("POST", "/api/pets", t1, {"name": "旺财", "species": "dog", "gender": "male"})
pet1 = json.loads(b); print("customer1 pet", s, pet1["id"])
s, b = call("POST", "/api/pets", t2, {"name": "咪咪", "species": "cat"})
pet2 = json.loads(b); print("customer2 pet", s, pet2["id"])

s, b = call("POST", "/api/booking/appointments", t1, {"pet_id": pet1["id"], "store_id": storeA["id"], "appt_type": "grooming", "appt_time": "2026-09-25T10:00:00"})
print("customer1 appt to A", s)
s, b = call("POST", "/api/booking/appointments", t2, {"pet_id": pet2["id"], "store_id": storeB["id"], "appt_type": "exam", "appt_time": "2026-09-26T14:00:00"})
print("customer2 appt to B", s)
s, b = call("POST", "/api/booking/boardings", t1, {"pet_id": pet1["id"], "store_id": storeA["id"], "start_date": "2026-10-01", "end_date": "2026-10-03", "daily_fee": 88})
print("customer1 boarding to A", s)

# 店A店主也来一单自己店（店主本人可当主人）
tA = login("storeA_mgr", "Passw0rd!a")
s, b = call("POST", "/api/pets", tA, {"name": "皮皮", "species": "dog"})
print("storeA_mgr own pet", s)

# ---- 店间隔离验证 ----
ta_mgr = login("storeA_mgr", "Passw0rd!a")
tb_mgr = login("storeB_mgr", "Passw0rd!a")
ta_staff = login("storeA_staff", "Passw0rd!a")

s, b = call("GET", "/api/workspace/overview", ta_mgr)
print("A overview", s, b)
s, b = call("GET", "/api/workspace/overview", tb_mgr)
print("B overview", s, b)

s, b = call("GET", "/api/workspace/appointments", ta_mgr)
print("A sees appts:", b)
s, b = call("GET", "/api/workspace/appointments", tb_mgr)
print("B sees appts:", b)
s, b = call("GET", "/api/workspace/customers", ta_mgr)
print("A customers:", b)

# 普通用户访问工作台应 403
s, b = call("GET", "/api/workspace/overview", t1)
print("customer1 access workspace ->", s, "(expect 403)")

# 店员改状态
s, b = call("GET", "/api/workspace/appointments", ta_mgr)
appts = json.loads(b)
if appts:
    s, b = call("POST", f"/api/workspace/appointments/{appts[0]['id']}/status", ta_staff, {"status": "confirmed"})
    print("staff of A confirm A appt ->", s)

# A 店员尝试改 B 的预约（应 404，隔离）
s, b = call("GET", "/api/workspace/appointments", tb_mgr)
b_appts = json.loads(b)
if b_appts:
    sid = b_appts[0]["id"]
    s2, b2 = call("POST", f"/api/workspace/appointments/{sid}/status", ta_staff, {"status": "confirmed"})
    print(f"staff of A modify B appt {sid} ->", s2, "(expect 404)")

# 商品：A 店员建商品只能归属 A；改 B 商品 404
s, b = call("POST", "/api/stores/products", ta_staff, {"name": "A店猫咪抓板", "category": "toy", "store_id": storeB["id"]})
print("A staff create product into B ->", s, "(expect 403)")
s, b = call("POST", "/api/stores/products", ta_staff, {"name": "A店狗粮10kg", "category": "food", "species": "dog"})
print("A staff create own product ->", s)
s, b = call("GET", "/api/stores/products", ta_staff)
print("products list:", b)