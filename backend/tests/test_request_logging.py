
import re

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.core.logging_config import request_id_var
from app.core.request_logging import RequestLoggingMiddleware


@pytest.fixture
def test_app():
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/test")
    async def test_endpoint(request: Request):
        return {
            "request_id": request_id_var.get(),
        }

    return app


@pytest.mark.asyncio
async def test_existing_request_id(test_app):
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/test",
            headers={"X-Request-ID": "resolveops-test-001"},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "resolveops-test-001"
    assert response.json()["request_id"] == "resolveops-test-001"


@pytest.mark.asyncio
async def test_generated_request_id(test_app):
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/test")

    request_id = response.headers["X-Request-ID"]

    assert request_id
    assert response.json()["request_id"] == request_id
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-"
        r"[0-9a-f]{4}-[0-9a-f]{4}-"
        r"[0-9a-f]{12}",
        request_id,
    )


@pytest.mark.asyncio
async def test_invalid_request_id_replaced(test_app):
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/test",
            headers={"X-Request-ID": "invalid id with spaces"},
        )

    request_id = response.headers["X-Request-ID"]

    assert request_id != "invalid id with spaces"
    assert response.json()["request_id"] == request_id


@pytest.mark.asyncio
async def test_request_id_does_not_leak(test_app):
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        first = await client.get(
            "/test",
            headers={"X-Request-ID": "first-request"},
        )

        second = await client.get(
            "/test",
            headers={"X-Request-ID": "second-request"},
        )

    assert first.json()["request_id"] == "first-request"
    assert second.json()["request_id"] == "second-request"
    assert request_id_var.get() is None
