"""商品订单状态机：合法流转成功，非法流转拒绝，跨店改单 404。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import assign_staff, auth, create_store, login, register, uniq


@pytest.fixture()
def order_world(client: TestClient, admin_token: str) -> dict:
    mgr_a = register(client, uniq("omgrA"))
    mgr_b = register(client, uniq("omgrB"))
    buyer = register(client, uniq("obuy"))
    store_a = create_store(client, admin_token, uniq("单A"), "shop")
    store_b = create_store(client, admin_token, uniq("单B"), "shop")
    assign_staff(client, admin_token, store_a["id"], mgr_a["id"], "manager")
    assign_staff(client, admin_token, store_b["id"], mgr_b["id"], "manager")
    token_a = login(client, mgr_a["username"])
    token_b = login(client, mgr_b["username"])
    token_user = login(client, buyer["username"])

    product = client.post(
        "/api/stores/products",
        headers=auth(token_a),
        json={
            "name": uniq("狗粮"),
            "category": "food",
            "species": "dog",
            "price": 10,
            "stock": 5,
        },
    )
    assert product.status_code == 200, product.text
    return {
        "token_a": token_a,
        "token_b": token_b,
        "token_user": token_user,
        "store_a": store_a,
        "product": product.json(),
    }


def _place(client: TestClient, world: dict, qty: int = 1) -> dict:
    resp = client.post(
        "/api/orders",
        headers=auth(world["token_user"]),
        json={
            "items": [{"product_id": world["product"]["id"], "qty": qty}],
            "address": "上海示范路 1 号",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["store_id"] == world["store_a"]["id"]
    assert body["total"] == 10 * qty
    assert body["items"][0]["qty"] == qty
    return body


def _set_status(client: TestClient, token: str, order_id: int, status: str):
    return client.post(
        f"/api/orders/{order_id}/status",
        headers=auth(token),
        json={"status": status},
    )


def test_legal_order_transitions(client: TestClient, order_world: dict):
    order = _place(client, order_world)
    current = "pending"
    for nxt in ("accepted", "preparing", "delivering", "completed"):
        resp = _set_status(client, order_world["token_a"], order["id"], nxt)
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == nxt
        assert resp.json()["id"] == order["id"]
        current = nxt
    assert current == "completed"

    stuck = _set_status(client, order_world["token_a"], order["id"], "cancelled")
    assert stuck.status_code == 400, stuck.text


def test_illegal_order_transition_is_rejected(client: TestClient, order_world: dict):
    order = _place(client, order_world)
    jump = _set_status(client, order_world["token_a"], order["id"], "completed")
    assert jump.status_code == 400, jump.text
    assert "pending" in jump.json()["detail"]

    listed = client.get("/api/orders/store", headers=auth(order_world["token_a"]))
    assert listed.status_code == 200, listed.text
    matched = next(row for row in listed.json() if row["id"] == order["id"])
    assert matched["status"] == "pending"

    unknown = _set_status(client, order_world["token_a"], order["id"], "refunded")
    assert unknown.status_code == 400, unknown.text


def test_customer_cannot_advance_order_and_other_store_gets_404(
    client: TestClient, order_world: dict
):
    order = _place(client, order_world)
    customer = _set_status(client, order_world["token_user"], order["id"], "accepted")
    assert customer.status_code == 403, customer.text

    foreign = _set_status(client, order_world["token_b"], order["id"], "accepted")
    assert foreign.status_code == 404, foreign.text

    own = client.get("/api/orders", headers=auth(order_world["token_user"]))
    assert own.status_code == 200, own.text
    assert next(row["status"] for row in own.json() if row["id"] == order["id"]) == "pending"

    other_list = client.get("/api/orders/store", headers=auth(order_world["token_b"]))
    assert other_list.status_code == 200, other_list.text
    assert order["id"] not in {row["id"] for row in other_list.json()}


def test_cancel_pending_restores_stock(client: TestClient, order_world: dict):
    before = client.get(
        f"/api/stores/products/{order_world['product']['id']}",
        headers=auth(order_world["token_user"]),
    )
    assert before.status_code == 200, before.text
    stock_before = before.json()["stock"]

    order = _place(client, order_world, qty=2)
    mid = client.get(
        f"/api/stores/products/{order_world['product']['id']}",
        headers=auth(order_world["token_user"]),
    )
    assert mid.json()["stock"] == stock_before - 2

    cancelled = client.post(
        f"/api/orders/{order['id']}/cancel",
        headers=auth(order_world["token_user"]),
    )
    assert cancelled.status_code == 200, cancelled.text
    after = client.get(
        f"/api/stores/products/{order_world['product']['id']}",
        headers=auth(order_world["token_user"]),
    )
    assert after.json()["stock"] == stock_before

    again = client.post(
        f"/api/orders/{order['id']}/cancel",
        headers=auth(order_world["token_user"]),
    )
    assert again.status_code == 400, again.text
