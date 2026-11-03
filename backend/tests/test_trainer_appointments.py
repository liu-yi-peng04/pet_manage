"""训犬师 train 预约：创建、身份、以及教练之间的隔离。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth, login, register, uniq


def _profile(client: TestClient, token: str, display_name: str) -> dict:
    resp = client.post(
        "/api/trainers/me",
        headers=auth(token),
        json={
            "display_name": display_name,
            "city": "上海",
            "specialties": "服从",
            "years": 3,
            "bio": "测试教练",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_train_appointment_create_permission_and_isolation(
    client: TestClient, admin_token: str
):
    owner = register(client, uniq("own"))
    trainer_user = register(client, uniq("trn"), role="trainer")
    other_trainer_user = register(client, uniq("otn"), role="trainer")
    plain = register(client, uniq("pln"))
    token_owner = login(client, owner["username"])
    token_trainer = login(client, trainer_user["username"])
    token_other = login(client, other_trainer_user["username"])
    token_plain = login(client, plain["username"])

    pet = client.post(
        "/api/pets",
        headers=auth(token_owner),
        json={"name": "训练犬", "species": "dog", "allergies": "花生过敏仅主人可见"},
    )
    assert pet.status_code == 200, pet.text
    pet_id = pet.json()["id"]

    # 普通用户不能打开训犬师收件箱
    denied = client.get("/api/booking/trainer/appointments", headers=auth(token_plain))
    assert denied.status_code == 403, denied.text

    # 非养宠用户不能发起预约
    staffish = client.post(
        "/api/booking/appointments",
        headers=auth(token_trainer),
        json={"appt_type": "train", "appt_time": "2026-10-01T09:00:00", "trainer_id": 1},
    )
    assert staffish.status_code == 403, staffish.text

    missing = client.post(
        "/api/booking/appointments",
        headers=auth(token_owner),
        json={"pet_id": pet_id, "appt_type": "train", "appt_time": "2026-10-01T09:00:00"},
    )
    assert missing.status_code == 400, missing.text

    profile = _profile(client, token_trainer, uniq("林"))
    other_profile = _profile(client, token_other, uniq("周"))
    assert profile["verified"] is False

    unverified = client.post(
        "/api/booking/appointments",
        headers=auth(token_owner),
        json={
            "pet_id": pet_id,
            "trainer_id": profile["id"],
            "appt_type": "train",
            "appt_time": "2026-10-01T09:00:00",
        },
    )
    assert unverified.status_code == 400, unverified.text

    # 非管理员不能审核
    sneak = client.post(
        f"/api/trainers/{profile['id']}/verify",
        headers=auth(token_owner),
    )
    assert sneak.status_code == 403, sneak.text

    verified = client.post(
        f"/api/trainers/{profile['id']}/verify",
        headers=auth(admin_token),
    )
    assert verified.status_code == 200, verified.text
    other_ok = client.post(
        f"/api/trainers/{other_profile['id']}/verify",
        headers=auth(admin_token),
    )
    assert other_ok.status_code == 200, other_ok.text

    created = client.post(
        "/api/booking/appointments",
        headers=auth(token_owner),
        json={
            "pet_id": pet_id,
            "trainer_id": profile["id"],
            "appt_type": "train",
            "appt_time": "2026-10-01T09:00:00",
            "notes": "拆家",
        },
    )
    assert created.status_code == 200, created.text
    appt = created.json()
    assert appt["appt_type"] == "train"
    assert appt["status"] == "pending"
    assert appt["trainer_id"] == profile["id"]
    assert appt["store_id"] is None
    assert appt["pet_id"] == pet_id

    mine = client.get("/api/booking/appointments", headers=auth(token_owner))
    assert mine.status_code == 200, mine.text
    assert appt["id"] in {row["id"] for row in mine.json()}

    inbox = client.get("/api/booking/trainer/appointments", headers=auth(token_trainer))
    assert inbox.status_code == 200, inbox.text
    assert [row["id"] for row in inbox.json() if row["id"] == appt["id"]] == [appt["id"]]

    other_inbox = client.get("/api/booking/trainer/appointments", headers=auth(token_other))
    assert other_inbox.status_code == 200, other_inbox.text
    assert appt["id"] not in {row["id"] for row in other_inbox.json()}

    hijack = client.post(
        f"/api/booking/trainer/appointments/{appt['id']}/status",
        headers=auth(token_other),
        json={"status": "confirmed"},
    )
    assert hijack.status_code == 404, hijack.text

    plain_set = client.post(
        f"/api/booking/trainer/appointments/{appt['id']}/status",
        headers=auth(token_plain),
        json={"status": "confirmed"},
    )
    assert plain_set.status_code == 403, plain_set.text

    confirmed = client.post(
        f"/api/booking/trainer/appointments/{appt['id']}/status",
        headers=auth(token_trainer),
        json={"status": "confirmed"},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "confirmed"
    assert confirmed.json()["trainer_id"] == profile["id"]
