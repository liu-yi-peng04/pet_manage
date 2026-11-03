"""跨店写路径：在工作台预约之外，再覆盖商品、订单、待售宠、疫苗代约。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import assign_staff, auth, create_store, login, register, uniq


def _shop(client: TestClient, admin_token: str, prefix: str) -> tuple[dict, str]:
    user = register(client, uniq(prefix))
    store = create_store(client, admin_token, uniq(prefix), "shop")
    assign_staff(client, admin_token, store["id"], user["id"], "manager")
    return store, login(client, user["username"])


def test_cross_store_product_update_and_delete_are_404(client: TestClient, admin_token: str):
    store_a, token_a = _shop(client, admin_token, "pwA")
    _store_b, token_b = _shop(client, admin_token, "pwB")
    created = client.post(
        "/api/stores/products",
        headers=auth(token_a),
        json={"name": uniq("商品"), "category": "supply", "price": 12, "stock": 3},
    )
    assert created.status_code == 200, created.text
    product = created.json()
    assert product["store_id"] == store_a["id"]

    payload = {
        "name": "改名",
        "category": "supply",
        "price": 12,
        "stock": 3,
        "store_id": store_a["id"],
    }
    updated = client.put(
        f"/api/stores/products/{product['id']}",
        headers=auth(token_b),
        json=payload,
    )
    assert updated.status_code == 404, updated.text

    deleted = client.delete(
        f"/api/stores/products/{product['id']}",
        headers=auth(token_b),
    )
    assert deleted.status_code == 404, deleted.text

    still = client.get(f"/api/stores/products/{product['id']}", headers=auth(token_a))
    assert still.status_code == 200, still.text
    assert still.json()["name"] == product["name"]

    # 本店改到别的店也要拒绝
    move = client.put(
        f"/api/stores/products/{product['id']}",
        headers=auth(token_a),
        json={**payload, "store_id": _store_b["id"], "name": "试图搬走"},
    )
    assert move.status_code == 403, move.text


def test_cross_store_listing_delete_is_404(client: TestClient, admin_token: str):
    _store_a, token_a = _shop(client, admin_token, "lsA")
    _store_b, token_b = _shop(client, admin_token, "lsB")
    created = client.post(
        "/api/workspace/listings",
        headers=auth(token_a),
        json={"name": uniq("待售"), "species": "dog", "price": 1000},
    )
    assert created.status_code == 200, created.text
    listing_id = created.json()["id"]
    assert created.json()["store_id"] == _store_a["id"]

    foreign = client.delete(f"/api/workspace/listings/{listing_id}", headers=auth(token_b))
    assert foreign.status_code == 404, foreign.text

    own_list = client.get("/api/workspace/listings", headers=auth(token_a))
    other_list = client.get("/api/workspace/listings", headers=auth(token_b))
    assert listing_id in {row["id"] for row in own_list.json()}
    assert listing_id not in {row["id"] for row in other_list.json()}

    removed = client.delete(f"/api/workspace/listings/{listing_id}", headers=auth(token_a))
    assert removed.status_code == 200, removed.text


def test_cross_store_order_is_invisible_and_vaccine_invite_rejects_foreign_pet(
    client: TestClient, admin_token: str
):
    store_a, token_a = _shop(client, admin_token, "vxA")
    _store_b, token_b = _shop(client, admin_token, "vxB")
    buyer = register(client, uniq("vbuy"))
    token_user = login(client, buyer["username"])
    pet = client.post(
        "/api/pets",
        headers=auth(token_user),
        json={"name": "只去过B概念店的宠物", "species": "dog"},
    )
    assert pet.status_code == 200, pet.text

    # 宠物只在 B 店有预约，A 店代约应 404
    booked = client.post(
        "/api/booking/appointments",
        headers=auth(token_user),
        json={
            "pet_id": pet.json()["id"],
            "store_id": _store_b["id"],
            "appt_type": "grooming",
            "appt_time": "2026-12-01T11:00:00",
        },
    )
    assert booked.status_code == 200, booked.text

    hospitals = client.get(
        "/api/stores",
        headers=auth(token_a),
        params={"store_type": "hospital"},
    )
    assert hospitals.status_code == 200, hospitals.text
    assert hospitals.json(), "启动种子应至少有一家医院"
    hospital_id = hospitals.json()[0]["id"]

    invite = client.post(
        "/api/workspace/vaccine-recalls/invite",
        headers=auth(token_a),
        json={"pet_id": pet.json()["id"], "hospital_id": hospital_id},
    )
    assert invite.status_code == 404, invite.text

    # B 店客户本人可以下 A 店商品订单，但 B 店员工不能改这张单
    product = client.post(
        "/api/stores/products",
        headers=auth(token_a),
        json={"name": uniq("罐头"), "category": "food", "price": 8, "stock": 4},
    )
    assert product.status_code == 200, product.text
    order = client.post(
        "/api/orders",
        headers=auth(token_user),
        json={
            "items": [{"product_id": product.json()["id"], "qty": 1}],
            "address": "测试地址",
        },
    )
    assert order.status_code == 200, order.text
    assert order.json()["store_id"] == store_a["id"]

    touch = client.post(
        f"/api/orders/{order.json()['id']}/status",
        headers=auth(token_b),
        json={"status": "accepted"},
    )
    assert touch.status_code == 404, touch.text
    ok = client.post(
        f"/api/orders/{order.json()['id']}/status",
        headers=auth(token_a),
        json={"status": "accepted"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "accepted"
