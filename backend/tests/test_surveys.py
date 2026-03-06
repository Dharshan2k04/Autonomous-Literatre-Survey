import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestSurveys:
    async def _get_token(self, client: AsyncClient, email: str = "survey@example.com") -> str:
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "StrongPass123!",
                "full_name": "Survey User",
            },
        )
        return reg.json()["tokens"]["access_token"]

    async def test_create_survey(self, client: AsyncClient):
        token = await self._get_token(client, "create_survey@example.com")
        response = await client.post(
            "/api/v1/surveys",
            json={
                "topic": "Machine Learning in Healthcare",
                "description": "A survey on ML applications in healthcare",
                "max_papers": 20,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["topic"] == "Machine Learning in Healthcare"
        assert data["status"] == "pending"

    async def test_list_surveys(self, client: AsyncClient):
        token = await self._get_token(client, "list_survey@example.com")
        # Create a survey first
        await client.post(
            "/api/v1/surveys",
            json={"topic": "NLP Survey", "max_papers": 10},
            headers={"Authorization": f"Bearer {token}"},
        )
        response = await client.get(
            "/api/v1/surveys",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "surveys" in data
        assert len(data["surveys"]) >= 1

    async def test_create_survey_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/surveys",
            json={"topic": "Test", "max_papers": 10},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestSurveyDetail:
    async def test_get_survey(self, client: AsyncClient):
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "detail@example.com",
                "password": "StrongPass123!",
                "full_name": "Detail User",
            },
        )
        token = reg.json()["tokens"]["access_token"]
        create = await client.post(
            "/api/v1/surveys",
            json={"topic": "Detail Survey", "max_papers": 10},
            headers={"Authorization": f"Bearer {token}"},
        )
        survey_id = create.json()["id"]
        response = await client.get(
            f"/api/v1/surveys/{survey_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["topic"] == "Detail Survey"

    async def test_get_nonexistent_survey(self, client: AsyncClient):
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "nosurvey@example.com",
                "password": "StrongPass123!",
                "full_name": "No Survey",
            },
        )
        token = reg.json()["tokens"]["access_token"]
        response = await client.get(
            "/api/v1/surveys/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
