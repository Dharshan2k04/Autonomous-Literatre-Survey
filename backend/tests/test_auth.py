import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuthRegister:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "StrongPass123!",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "tokens" in data
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]
        assert data["user"]["email"] == "test@example.com"

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {
            "email": "dupe@example.com",
            "password": "StrongPass123!",
            "full_name": "First",
        }
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409

    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "StrongPass123!",
                "full_name": "Test",
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestAuthLogin:
    async def test_login_success(self, client: AsyncClient):
        # Register first
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@example.com",
                "password": "StrongPass123!",
                "full_name": "Login User",
            },
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "StrongPass123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data["tokens"]

    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrong@example.com",
                "password": "StrongPass123!",
                "full_name": "Wrong",
            },
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@example.com", "password": "BadPassword"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestAuthMe:
    async def test_get_me_authenticated(self, client: AsyncClient):
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "me@example.com",
                "password": "StrongPass123!",
                "full_name": "Me User",
            },
        )
        token = reg.json()["tokens"]["access_token"]
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "me@example.com"

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401
