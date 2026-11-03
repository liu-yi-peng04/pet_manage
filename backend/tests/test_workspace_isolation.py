"""门店工作台隔离。

对应原 ``backend/test_workspace.py`` 的手工脚本：
两家店、店主/店员/普通用户，断言跨店看不见、改不了。

医院类型门店当前拒绝通过员工接口加人（400），
因此两家店都用 ``shop``，才能分配店员并覆盖原脚本的隔离意图。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import (
    PASSWORD,
    assign_staff,
    auth,
    create_store,
    login,
    register,
    uniq,
)


@pytest.fixture()
def world(client: TestClient, admin_token: str) -> dict:
    names = {
        "mgr_a": uniq("mgrA"),
        "mgr_b": uniq("mgrB"),
        "staff_a": uniq("stfA"),
        "cust_a": uniq("cusA"),
        "cust_b": uniq("cusB"),
    }
    users = {key: register(client, username) for key, username in names.items()}
    store_a = create_store(client, admin_token, uniq("店A"), "shop")
    store_b = create_store(client, admin_token, uniq("店B"), "shop")
    assign_staff(client, admin_token, store_a["id"], users["mgr_a"]["id"], "manager")
    assign_staff(client, admin_token, store_a["id"], users["staff_a"]["id"], "assistant")
    assign_staff(client, admin_token, store_b["id"], users["mgr_b"]["id"], "manager")

    tokens = {key: login(client, username) for key, username in names.items()}

    pet_a = client.post(
        "/api/pets",
        headers=auth(tokens["cust_a"]),
        json={"name": "旺财", "species": "dog", "gender": "male"},
    )
    assert pet_a.status_code == 200, pet_a.text
    pet_b = client.post(
        "/api/pets",
        headers=auth(tokens["cust_b"]),
        json={"name": "咪咪", "species": "cat"},
    )
    assert pet_b.status_code == 200, pet_b.text

    appt_a = client.post(
        "/api/booking/appointments",
        headers=auth(tokens["cust_a"]),
        json={
            "pet_id": pet_a.json()["id"],
            "store_id": store_a["id"],
            "appt_type": "grooming",
            "appt_time": "2026-09-25T10:00:00",
        },
    )
    assert appt_a.status_code == 200, appt_a.text
    appt_b = client.post(
        "/api/booking/appointments",
        headers=auth(tokens["cust_b"]),
        json={
            "pet_id": pet_b.json()["id"],
            "store_id": store_b["id"],
            "appt_type": "grooming",
            "appt_time": "2026-09-26T14:00:00",
        },
    )
    assert appt_b.status_code == 200, appt_b.text
    boarding = client.post(
        "/api/booking/boardings",
        headers=auth(tokens["cust_a"]),
        json={
            "pet_id": pet_a.json()["id"],
            "store_id": store_a["id"],
            "start_date": "2026-10-01",
            "end_date": "2026-10-03",
            "daily_fee": 88,
        },
    )
    assert boarding.status_code == 200, boarding.text

    return {
        "names": names,
        "users": users,
        "tokens": tokens,
        "store_a": store_a,
        "store_b": store_b,
        "pet_a": pet_a.json(),
        "pet_b": pet_b.json(),
        "appt_a": appt_a.json(),
        "appt_b": appt_b.json(),
        "boarding": boarding.json(),
        "password": PASSWORD,
    }


def _ids(rows: list[dict]) -> set[int]:
    return {row["id"] for row in rows}


def test_overview_is_scoped_to_own_store(client: TestClient, world: dict):
    resp_a = client.get("/api/workspace/overview", headers=auth(world["tokens"]["mgr_a"]))
    resp_b = client.get("/api/workspace/overview", headers=auth(world["tokens"]["mgr_b"]))
    assert resp_a.status_code == 200, resp_a.text
    assert resp_b.status_code == 200, resp_b.text

    body_a = resp_a.json()
    body_b = resp_b.json()
    assert body_a["store"]["id"] == world["store_a"]["id"]
    assert body_b["store"]["id"] == world["store_b"]["id"]
    assert body_a["store"]["name"] == world["store_a"]["name"]
    assert body_b["pending_appointments"] == 1
    assert body_a["pending_appointments"] == 1
    assert body_a["active_boardings"] == 1
    assert body_b["active_boardings"] == 0
    assert body_a["customers"] == 1
    assert body_b["customers"] == 1


def test_appointments_and_customers_do_not_cross_stores(client: TestClient, world: dict):
    appt_a = client.get("/api/workspace/appointments", headers=auth(world["tokens"]["mgr_a"]))
    appt_b = client.get("/api/workspace/appointments", headers=auth(world["tokens"]["mgr_b"]))
    assert appt_a.status_code == 200, appt_a.text
    assert appt_b.status_code == 200, appt_b.text
    ids_a = _ids(appt_a.json())
    ids_b = _ids(appt_b.json())
    assert world["appt_a"]["id"] in ids_a
    assert world["appt_b"]["id"] in ids_b
    assert ids_a.isdisjoint(ids_b)
    # 用 pet_id 区分。出参里的 pet_name 目前恒为 null，见缺口清单。
    assert {row["pet_id"] for row in appt_a.json()} == {world["pet_a"]["id"]}
    assert {row["pet_id"] for row in appt_b.json()} == {world["pet_b"]["id"]}

    cust_a = client.get("/api/workspace/customers", headers=auth(world["tokens"]["mgr_a"]))
    cust_b = client.get("/api/workspace/customers", headers=auth(world["tokens"]["mgr_b"]))
    assert cust_a.status_code == 200, cust_a.text
    assert cust_b.status_code == 200, cust_b.text
    assert {row["username"] for row in cust_a.json()} == {world["names"]["cust_a"]}
    assert {row["username"] for row in cust_b.json()} == {world["names"]["cust_b"]}


def test_customer_cannot_open_workspace(client: TestClient, world: dict):
    headers = auth(world["tokens"]["cust_a"])
    for path in (
        "/api/workspace/overview",
        "/api/workspace/appointments",
        "/api/workspace/boardings",
        "/api/workspace/customers",
        "/api/workspace/products",
    ):
        resp = client.get(path, headers=headers)
        assert resp.status_code == 403, (path, resp.text)


def test_own_staff_can_confirm_appointment_and_boarding(client: TestClient, world: dict):
    headers = auth(world["tokens"]["staff_a"])
    resp = client.post(
        f"/api/workspace/appointments/{world['appt_a']['id']}/status",
        headers=headers,
        json={"status": "confirmed"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["detail"] == "已更新"

    listed = client.get("/api/workspace/appointments", headers=auth(world["tokens"]["mgr_a"]))
    assert listed.status_code == 200, listed.text
    matched = next(row for row in listed.json() if row["id"] == world["appt_a"]["id"])
    assert matched["status"] == "confirmed"

    boarding = client.post(
        f"/api/workspace/boardings/{world['boarding']['id']}/status",
        headers=headers,
        json={"status": "confirmed"},
    )
    assert boarding.status_code == 200, boarding.text
    rows = client.get("/api/workspace/boardings", headers=headers)
    assert rows.status_code == 200, rows.text
    matched_boarding = next(row for row in rows.json() if row["id"] == world["boarding"]["id"])
    assert matched_boarding["status"] == "confirmed"
    assert matched_boarding["store_id"] == world["store_a"]["id"]


def test_cross_store_status_update_is_404(client: TestClient, world: dict):
    headers = auth(world["tokens"]["staff_a"])
    appt = client.post(
        f"/api/workspace/appointments/{world['appt_b']['id']}/status",
        headers=headers,
        json={"status": "confirmed"},
    )
    assert appt.status_code == 404, appt.text

    boarding_resp = client.post(
        "/api/booking/boardings",
        headers=auth(world["tokens"]["cust_b"]),
        json={
            "pet_id": world["pet_b"]["id"],
            "store_id": world["store_b"]["id"],
            "start_date": "2026-11-01",
            "end_date": "2026-11-02",
            "daily_fee": 60,
        },
    )
    assert boarding_resp.status_code == 200, boarding_resp.text
    foreign_boarding = boarding_resp.json()
    denied = client.post(
        f"/api/workspace/boardings/{foreign_boarding['id']}/status",
        headers=headers,
        json={"status": "confirmed"},
    )
    assert denied.status_code == 404, denied.text

    still = client.get("/api/workspace/appointments", headers=auth(world["tokens"]["mgr_b"]))
    matched = next(row for row in still.json() if row["id"] == world["appt_b"]["id"])
    assert matched["status"] == "pending"


def test_unknown_appointment_status_is_400(client: TestClient, world: dict):
    resp = client.post(
        f"/api/workspace/appointments/{world['appt_a']['id']}/status",
        headers=auth(world["tokens"]["staff_a"]),
        json={"status": "teleported"},
    )
    assert resp.status_code == 400, resp.text


def test_staff_product_stays_in_own_store(client: TestClient, world: dict):
    headers = auth(world["tokens"]["staff_a"])
    foreign = client.post(
        "/api/stores/products",
        headers=headers,
        json={
            "name": "A店猫咪抓板",
            "category": "toy",
            "store_id": world["store_b"]["id"],
        },
    )
    assert foreign.status_code == 403, foreign.text

    own = client.post(
        "/api/stores/products",
        headers=headers,
        json={"name": "A店狗粮10kg", "category": "food", "species": "dog", "price": 199},
    )
    assert own.status_code == 200, own.text
    body = own.json()
    assert body["name"] == "A店狗粮10kg"
    assert body["store_id"] == world["store_a"]["id"]
    assert body["category"] == "food"

    listed_a = client.get("/api/workspace/products", headers=headers)
    listed_b = client.get("/api/workspace/products", headers=auth(world["tokens"]["mgr_b"]))
    assert listed_a.status_code == 200, listed_a.text
    assert listed_b.status_code == 200, listed_b.text
    assert body["id"] in _ids(listed_a.json())
    assert body["id"] not in _ids(listed_b.json())
    assert all(row["store_id"] == world["store_a"]["id"] for row in listed_a.json())


def test_customer_and_admin_cannot_create_product(client: TestClient, admin_token: str, world: dict):
    customer = client.post(
        "/api/stores/products",
        headers=auth(world["tokens"]["cust_a"]),
        json={"name": "用户自建商品", "category": "toy"},
    )
    assert customer.status_code == 403, customer.text

    admin = client.post(
        "/api/stores/products",
        headers=auth(admin_token),
        json={"name": "超管自建商品", "category": "toy", "store_id": world["store_a"]["id"]},
    )
    assert admin.status_code == 403, admin.text


def test_hospital_rejects_staff_assignment(client: TestClient, admin_token: str):
    """现网规则：医院不设职工账号。旧脚本把 B 店建成医院再加人，现在会 400。"""
    hospital = create_store(client, admin_token, uniq("医院"), "hospital")
    user = register(client, uniq("hospU"))
    resp = client.post(
        f"/api/stores/{hospital['id']}/staff",
        headers=auth(admin_token),
        json={"user_id": user["id"], "staff_role": "manager"},
    )
    assert resp.status_code == 400, resp.text
