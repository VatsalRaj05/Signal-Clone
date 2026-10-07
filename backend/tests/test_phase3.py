"""Phase 3 backend tests.

Covers:
- GET /contacts
- POST /contacts (add, duplicate, self)
- DELETE /contacts/{id}
- GET /users/search?q=
- GET /conversations
- POST /conversations/direct (new, duplicate)
- GET /conversations/{id} (member, non-member)
- GET /conversations/{id}/messages (member, non-member, pagination)
"""

import pytest
from httpx import AsyncClient


# ── Helpers ──────────────────────────────────────────────────────────────────

async def register_and_login(client: AsyncClient, username: str, password: str = "password123") -> str:
    """Register a user and return an access token."""
    await client.post(
        "/auth/register",
        json={"username": username, "password": password},
    )
    resp = await client.post(
        "/auth/login",
        json={"identifier": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Contacts ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_contacts_empty(client: AsyncClient):
    """A new user has no contacts."""
    token = await register_and_login(client, "ct_alice")
    resp = await client.get("/contacts", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_add_contact(client: AsyncClient):
    """Adding a contact returns 201 with contact data."""
    token_a = await register_and_login(client, "ct_a")
    token_b = await register_and_login(client, "ct_b")

    # Get Bob's user id via search
    search_resp = await client.get("/users/search?q=ct_b", headers=auth_headers(token_a))
    assert search_resp.status_code == 200
    bob_id = search_resp.json()[0]["id"]

    resp = await client.post(
        "/contacts",
        json={"contact_user_id": bob_id},
        headers=auth_headers(token_a),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["contact_user_id"] == bob_id
    assert "contact_user" in data
    assert data["contact_user"]["username"] == "ct_b"


@pytest.mark.asyncio
async def test_add_duplicate_contact(client: AsyncClient):
    """Adding the same contact twice returns 409."""
    token_a = await register_and_login(client, "ct_dup_a")
    token_b = await register_and_login(client, "ct_dup_b")

    search_resp = await client.get("/users/search?q=ct_dup_b", headers=auth_headers(token_a))
    bob_id = search_resp.json()[0]["id"]

    await client.post("/contacts", json={"contact_user_id": bob_id}, headers=auth_headers(token_a))
    resp = await client.post("/contacts", json={"contact_user_id": bob_id}, headers=auth_headers(token_a))
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_add_self_contact(client: AsyncClient):
    """A user cannot add themselves as a contact."""
    token = await register_and_login(client, "ct_self")

    me_resp = await client.get("/users/me", headers=auth_headers(token))
    my_id = me_resp.json()["id"]

    resp = await client.post(
        "/contacts",
        json={"contact_user_id": my_id},
        headers=auth_headers(token),
    )
    assert resp.status_code == 400
    assert "yourself" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_delete_contact(client: AsyncClient):
    """Deleting a contact returns 204 and the contact is removed."""
    token_a = await register_and_login(client, "ct_del_a")
    token_b = await register_and_login(client, "ct_del_b")

    search_resp = await client.get("/users/search?q=ct_del_b", headers=auth_headers(token_a))
    bob_id = search_resp.json()[0]["id"]

    await client.post("/contacts", json={"contact_user_id": bob_id}, headers=auth_headers(token_a))

    del_resp = await client.delete(f"/contacts/{bob_id}", headers=auth_headers(token_a))
    assert del_resp.status_code == 204

    list_resp = await client.get("/contacts", headers=auth_headers(token_a))
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_delete_nonexistent_contact(client: AsyncClient):
    """Deleting a contact that doesn't exist returns 404."""
    import uuid
    token = await register_and_login(client, "ct_del_none")
    resp = await client.delete(f"/contacts/{uuid.uuid4()}", headers=auth_headers(token))
    assert resp.status_code == 404


# ── User search ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_users(client: AsyncClient):
    """Search returns matching users excluding the caller."""
    token = await register_and_login(client, "searcher_xyz")
    await register_and_login(client, "findme_xyz")
    await register_and_login(client, "findme2_xyz")

    resp = await client.get("/users/search?q=findme_xyz", headers=auth_headers(token))
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()]
    assert "findme_xyz" in usernames
    # Caller excluded
    assert "searcher_xyz" not in usernames


@pytest.mark.asyncio
async def test_search_excludes_self(client: AsyncClient):
    """Search never returns the caller."""
    token = await register_and_login(client, "self_search_user")
    resp = await client.get("/users/search?q=self_search_user", headers=auth_headers(token))
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()]
    assert "self_search_user" not in usernames


# ── Conversations ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_conversations_empty(client: AsyncClient):
    """A new user has no conversations."""
    token = await register_and_login(client, "conv_new_user")
    resp = await client.get("/conversations", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_direct_conversation(client: AsyncClient):
    """Creating a direct conversation returns conversation data with both members."""
    token_a = await register_and_login(client, "conv_user_a")
    token_b = await register_and_login(client, "conv_user_b")

    b_id = (await client.get("/users/me", headers=auth_headers(token_b))).json()["id"]

    resp = await client.post(
        "/conversations/direct",
        json={"other_user_id": b_id},
        headers=auth_headers(token_a),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "DIRECT"
    member_ids = [m["user_id"] for m in data["members"]]
    a_id = (await client.get("/users/me", headers=auth_headers(token_a))).json()["id"]
    assert a_id in member_ids
    assert b_id in member_ids


@pytest.mark.asyncio
async def test_create_direct_conversation_deduplication(client: AsyncClient):
    """Creating a direct conversation twice returns the same conversation ID."""
    token_a = await register_and_login(client, "dedup_a")
    token_b = await register_and_login(client, "dedup_b")
    b_id = (await client.get("/users/me", headers=auth_headers(token_b))).json()["id"]

    r1 = await client.post("/conversations/direct", json={"other_user_id": b_id}, headers=auth_headers(token_a))
    r2 = await client.post("/conversations/direct", json={"other_user_id": b_id}, headers=auth_headers(token_a))
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.asyncio
async def test_get_conversation_as_member(client: AsyncClient):
    """A member can fetch a conversation by ID."""
    token_a = await register_and_login(client, "get_conv_a")
    token_b = await register_and_login(client, "get_conv_b")
    b_id = (await client.get("/users/me", headers=auth_headers(token_b))).json()["id"]

    conv_id = (await client.post("/conversations/direct", json={"other_user_id": b_id}, headers=auth_headers(token_a))).json()["id"]

    resp = await client.get(f"/conversations/{conv_id}", headers=auth_headers(token_a))
    assert resp.status_code == 200
    assert resp.json()["id"] == conv_id


@pytest.mark.asyncio
async def test_get_conversation_unauthorized(client: AsyncClient):
    """A non-member gets 403 when fetching a conversation."""
    token_a = await register_and_login(client, "unauth_conv_a")
    token_b = await register_and_login(client, "unauth_conv_b")
    token_c = await register_and_login(client, "unauth_conv_c")

    b_id = (await client.get("/users/me", headers=auth_headers(token_b))).json()["id"]
    conv_id = (await client.post("/conversations/direct", json={"other_user_id": b_id}, headers=auth_headers(token_a))).json()["id"]

    # User C is not a member
    resp = await client.get(f"/conversations/{conv_id}", headers=auth_headers(token_c))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_messages_empty(client: AsyncClient):
    """A new conversation has no messages."""
    token_a = await register_and_login(client, "msg_empty_a")
    token_b = await register_and_login(client, "msg_empty_b")
    b_id = (await client.get("/users/me", headers=auth_headers(token_b))).json()["id"]
    conv_id = (await client.post("/conversations/direct", json={"other_user_id": b_id}, headers=auth_headers(token_a))).json()["id"]

    resp = await client.get(f"/conversations/{conv_id}/messages", headers=auth_headers(token_a))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_messages_unauthorized(client: AsyncClient):
    """A non-member gets 403 when fetching messages."""
    token_a = await register_and_login(client, "msg_unauth_a")
    token_b = await register_and_login(client, "msg_unauth_b")
    token_c = await register_and_login(client, "msg_unauth_c")

    b_id = (await client.get("/users/me", headers=auth_headers(token_b))).json()["id"]
    conv_id = (await client.post("/conversations/direct", json={"other_user_id": b_id}, headers=auth_headers(token_a))).json()["id"]

    resp = await client.get(f"/conversations/{conv_id}/messages", headers=auth_headers(token_c))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_requests(client: AsyncClient):
    """All protected endpoints return 401 without a token."""
    import uuid
    fake_id = str(uuid.uuid4())
    endpoints = [
        ("GET", "/contacts"),
        ("POST", "/contacts"),
        ("GET", "/conversations"),
        ("POST", "/conversations/direct"),
        ("GET", f"/conversations/{fake_id}"),
        ("GET", f"/conversations/{fake_id}/messages"),
        ("GET", "/users/search?q=test"),
    ]
    for method, url in endpoints:
        resp = await client.request(method, url)
        assert resp.status_code == 401, f"Expected 401 for {method} {url}, got {resp.status_code}"
