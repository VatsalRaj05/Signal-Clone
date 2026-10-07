import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.core.security import verify_password

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, db_session: AsyncSession):
    response = await client.post(
        "/auth/register",
        json={"username": "testuser", "phone": "+1234567890", "password": "password123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "User registered successfully"
    assert "user_id" in data
    assert data["mock_otp"] == "123456"

@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, db_session: AsyncSession):
    # First user
    await client.post(
        "/auth/register",
        json={"username": "duplicate_user", "password": "password123"}
    )
    
    # Second user with same username
    response = await client.post(
        "/auth/register",
        json={"username": "duplicate_user", "password": "password456"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already registered"

@pytest.mark.asyncio
async def test_verify_otp(client: AsyncClient, db_session: AsyncSession):
    # Register first
    await client.post(
        "/auth/register",
        json={"username": "otp_user", "phone": "+1122334455", "password": "password123"}
    )
    
    # Verify OTP
    response = await client.post(
        "/auth/verify",
        json={"identifier": "+1122334455", "otp": "123456"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "otp_user"
    assert data["user"]["phone"] == "+1122334455"

@pytest.mark.asyncio
async def test_login(client: AsyncClient, db_session: AsyncSession):
    # Register first
    await client.post(
        "/auth/register",
        json={"username": "login_user", "phone": "+9988776655", "password": "password123"}
    )
    
    # Login
    response = await client.post(
        "/auth/login",
        json={"identifier": "login_user", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "login_user"

@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient, db_session: AsyncSession):
    # Register
    await client.post(
        "/auth/register",
        json={"username": "profile_user", "password": "password123"}
    )
    
    # Login to get token
    login_response = await client.post(
        "/auth/login",
        json={"identifier": "profile_user", "password": "password123"}
    )
    token = login_response.json()["access_token"]
    
    # Update profile
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.put(
        "/users/me",
        json={"display_name": "Profile User Display", "avatar_url": "http://example.com/avatar.png"},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Profile User Display"
    assert data["avatar_url"] == "http://example.com/avatar.png"
    
    # Get profile to verify
    response = await client.get("/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Profile User Display"
