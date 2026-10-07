import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_message_receipt_flow(client: AsyncClient):
    # 1. Register Alice and Bob
    alice_reg = await client.post("/auth/register", json={
        "username": "receipt_alice",
        "password": "Password123!",
        "display_name": "Alice R"
    })
    assert alice_reg.status_code == 201
    alice_id = alice_reg.json()["user_id"]

    alice_log = await client.post("/auth/login", json={
        "identifier": "receipt_alice",
        "password": "Password123!"
    })
    assert alice_log.status_code == 200
    alice_token = alice_log.json()["access_token"]

    bob_reg = await client.post("/auth/register", json={
        "username": "receipt_bob",
        "password": "Password123!",
        "display_name": "Bob R"
    })
    assert bob_reg.status_code == 201
    bob_id = bob_reg.json()["user_id"]

    bob_log = await client.post("/auth/login", json={
        "identifier": "receipt_bob",
        "password": "Password123!"
    })
    assert bob_log.status_code == 200
    bob_token = bob_log.json()["access_token"]

    # 2. Alice starts direct conversation with Bob
    conv_res = await client.post(
        "/conversations/direct",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={"other_user_id": bob_id}
    )
    assert conv_res.status_code == 200
    conv_id = conv_res.json()["id"]

    # 3. Alice sends a message to Bob (Bob is currently offline)
    msg_res = await client.post(
        f"/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={"content": "Hello Bob from Alice!", "message_type": "TEXT"}
    )
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert msg_data["status"] == "SENT"
    assert len(msg_data["receipts"]) == 1
    assert msg_data["receipts"][0]["user_id"] == bob_id
    assert msg_data["receipts"][0]["status"] == "SENT"

    # 4. Bob reads the message
    read_res = await client.post(
        f"/conversations/{conv_id}/read",
        headers={"Authorization": f"Bearer {bob_token}"}
    )
    assert read_res.status_code == 200
    assert read_res.json()["read_count"] == 1

    # 5. Check message list for Alice now shows READ
    list_res = await client.get(
        f"/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert list_res.status_code == 200
    messages = list_res.json()
    assert len(messages) >= 1
    latest_msg = messages[-1]
    assert latest_msg["status"] == "READ"
    assert latest_msg["receipts"][0]["status"] == "READ"
