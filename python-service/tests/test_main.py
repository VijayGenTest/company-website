"""Unit tests for the Python FastAPI service."""
import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.anyio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.anyio
async def test_process_missing_fields():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/process", json={})
    assert resp.status_code == 422
