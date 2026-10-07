import pytest
from httpx import AsyncClient

async def register_and_login(client: AsyncClient, username: str, password: str = "password123") -> tuple[str, str]:
    reg = await client.post("/auth/register", json={"username": username, "password": password, "display_name": username})
    assert reg.status_code == 201
    user_id = reg.json()["user_id"]
    login = await client.post("/auth/login", json={"identifier": username, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]
    return token, user_id

@pytest.mark.asyncio
async def test_group_conversation_flow_and_permissions(client: AsyncClient):
    # 1. Register 3 users: Alice, Bob, Charlie, and Eve (outsider)
    token_alice, id_alice = await register_and_login(client, "grp_alice")
    token_bob, id_bob = await register_and_login(client, "grp_bob")
    token_charlie, id_charlie = await register_and_login(client, "grp_charlie")
    token_eve, id_eve = await register_and_login(client, "grp_eve")

    # 2. Alice creates a group with Bob and Charlie
    res_group = await client.post(
        "/conversations/group",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "name": "Design Team",
            "member_ids": [id_bob, id_charlie]
        }
    )
    assert res_group.status_code == 201
    group_data = res_group.json()
    assert group_data["type"] == "GROUP"
    assert group_data["name"] == "Design Team"
    group_id = group_data["id"]

    # Verify members and roles
    members = group_data["members"]
    assert len(members) == 3
    alice_member = next(m for m in members if m["user_id"] == id_alice)
    bob_member = next(m for m in members if m["user_id"] == id_bob)
    assert alice_member["role"] == "ADMIN"
    assert bob_member["role"] == "MEMBER"

    # 3. Alice sends a message to the group
    msg_res = await client.post(
        f"/conversations/{group_id}/messages",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={"content": "Welcome team!", "message_type": "TEXT"}
    )
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert msg_data["content"] == "Welcome team!"
    # Offline recipients get SENT receipts
    assert len(msg_data["receipts"]) == 2

    # 4. Bob fetches messages from group (authorized)
    bob_msgs_res = await client.get(
        f"/conversations/{group_id}/messages",
        headers={"Authorization": f"Bearer {token_bob}"}
    )
    assert bob_msgs_res.status_code == 200
    assert len(bob_msgs_res.json()) == 1

    # 5. Eve attempts to fetch group details (unauthorized -> 403)
    eve_conv_res = await client.get(
        f"/conversations/{group_id}",
        headers={"Authorization": f"Bearer {token_eve}"}
    )
    assert eve_conv_res.status_code == 403

    # 6. Eve attempts to send a message to group (unauthorized -> 403)
    eve_send_res = await client.post(
        f"/conversations/{group_id}/messages",
        headers={"Authorization": f"Bearer {token_eve}"},
        json={"content": "Intruder message", "message_type": "TEXT"}
    )
    assert eve_send_res.status_code == 403

    # 7. Eve attempts to read group messages (unauthorized -> 403)
    eve_msgs_res = await client.get(
        f"/conversations/{group_id}/messages",
        headers={"Authorization": f"Bearer {token_eve}"}
    )
    assert eve_msgs_res.status_code == 403
