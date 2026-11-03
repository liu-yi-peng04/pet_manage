"""AI 通道不串话。

不调用真实大模型：把 ``run_agent_last`` 换成回显，
只验证会话归属、channel 过滤，以及宠物档案不会进别人的提示词。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import assign_staff, auth, create_store, login, register, uniq

SECRET = "花生过敏SECRET"


def _stub_agent(monkeypatch, sink: dict):
    def fake_run_agent_last(messages, kb_id, user_id, loop, pet_id, store_id, agent_mode):
        sink["messages"] = messages
        sink["user_id"] = user_id
        sink["pet_id"] = pet_id
        sink["agent_mode"] = agent_mode
        visible = [m["content"] for m in messages if m["role"] != "system"]
        return "STUB:" + " || ".join(visible)

    monkeypatch.setattr("app.api.chat.agent_service.run_agent_last", fake_run_agent_last)


def test_users_do_not_share_conversations_or_pet_context(client: TestClient, monkeypatch):
    sink: dict = {}
    _stub_agent(monkeypatch, sink)

    user_a = register(client, uniq("chatA"))
    user_b = register(client, uniq("chatB"))
    token_a = login(client, user_a["username"])
    token_b = login(client, user_b["username"])

    pet = client.post(
        "/api/pets",
        headers=auth(token_a),
        json={"name": "豆豆", "species": "dog", "allergies": SECRET},
    )
    assert pet.status_code == 200, pet.text
    pet_id = pet.json()["id"]

    first = client.post(
        "/api/chat",
        headers=auth(token_a),
        json={
            "content": "只告诉主人的问题",
            "pet_id": pet_id,
            "consult_type": "pet",
        },
    )
    assert first.status_code == 200, first.text
    conv_id = first.json()["conversation_id"]
    assert SECRET in sink["messages"][0]["content"]
    assert sink["user_id"] == user_a["id"]
    assert sink["pet_id"] == pet_id
    assert first.json()["content"].startswith("STUB:")
    assert "只告诉主人的问题" in first.json()["content"]

    # 用户 B 拿 A 的会话 id 和宠物 id，不能续写 A 的历史，也不能读到过敏原文
    stolen = client.post(
        "/api/chat",
        headers=auth(token_b),
        json={
            "content": "我是另一个人",
            "conversation_id": conv_id,
            "pet_id": pet_id,
            "consult_type": "pet",
        },
    )
    assert stolen.status_code == 200, stolen.text
    assert stolen.json()["conversation_id"] != conv_id
    blob = "\n".join(m["content"] for m in sink["messages"])
    assert SECRET not in blob
    assert "只告诉主人的问题" not in blob
    assert sink["user_id"] == user_b["id"]
    assert sink["pet_id"] == pet_id
    assert stolen.json()["content"] == "STUB:我是另一个人"

    hist_a = client.get("/api/chat/conversations", headers=auth(token_a))
    hist_b = client.get("/api/chat/conversations", headers=auth(token_b))
    assert hist_a.status_code == 200, hist_a.text
    assert hist_b.status_code == 200, hist_b.text
    text_a = " ".join(row["content"] for row in hist_a.json())
    text_b = " ".join(row["content"] for row in hist_b.json())
    assert "只告诉主人的问题" in text_a
    assert "我是另一个人" not in text_a
    assert "我是另一个人" in text_b
    assert "只告诉主人的问题" not in text_b
    assert all(row["conversation_id"] == conv_id for row in hist_a.json())


def test_staff_channel_drops_user_history_and_pet_profile(
    client: TestClient, admin_token: str, monkeypatch
):
    sink: dict = {}
    _stub_agent(monkeypatch, sink)

    username = uniq("dual")
    user = register(client, username)
    token = login(client, username)
    pet = client.post(
        "/api/pets",
        headers=auth(token),
        json={"name": "双端宠物", "species": "cat", "allergies": SECRET},
    )
    assert pet.status_code == 200, pet.text

    user_chat = client.post(
        "/api/chat",
        headers=auth(token),
        json={
            "content": "用户通道的私密句",
            "pet_id": pet.json()["id"],
            "consult_type": "pet",
        },
    )
    assert user_chat.status_code == 200, user_chat.text
    user_conv = user_chat.json()["conversation_id"]

    store = create_store(client, admin_token, uniq("聊店"), "shop")
    assign_staff(client, admin_token, store["id"], user["id"], "assistant")
    # 同一 token 仍指向该用户；角色已变成 staff，通道应切到 staff
    staff_chat = client.post(
        "/api/chat",
        headers=auth(token),
        json={
            "content": "店员通道的问题",
            "conversation_id": user_conv,
            "pet_id": pet.json()["id"],
            "consult_type": "pet",
        },
    )
    # 商家端禁止走养宠顾问
    assert staff_chat.status_code == 400, staff_chat.text

    staff_policy = client.post(
        "/api/chat",
        headers=auth(token),
        json={
            "content": "店员通道的问题",
            "conversation_id": user_conv,
            "pet_id": pet.json()["id"],
            "consult_type": "policy",
        },
    )
    assert staff_policy.status_code == 200, staff_policy.text
    assert staff_policy.json()["conversation_id"] != user_conv
    blob = "\n".join(m["content"] for m in sink["messages"])
    assert SECRET not in blob
    assert "用户通道的私密句" not in blob
    assert sink["pet_id"] is None
    assert sink["agent_mode"] == "store"
    assert "店员通道的问题" in staff_policy.json()["content"]

    listed = client.get("/api/chat/conversations", headers=auth(token))
    assert listed.status_code == 200, listed.text
    contents = " ".join(row["content"] for row in listed.json())
    assert "店员通道的问题" in contents
    assert "用户通道的私密句" not in contents
