import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from app.database import get_db_session
from starlette.requests import Request

from app.main import app, unexpected_error


async def test_health_check_reports_database_connection() -> None:
    fake_session = AsyncMock()

    async def override_session() -> AsyncIterator[AsyncMock]:
        yield fake_session

    app.dependency_overrides[get_db_session] = override_session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/health",
                headers={"X-Request-ID": "health-test-request"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}
    assert response.headers["X-Request-ID"] == "health-test-request"
    fake_session.execute.assert_awaited_once()


async def test_unexpected_error_returns_safe_response_with_request_id() -> None:
    request = Request({"type": "http", "method": "GET", "path": "/broken", "headers": []})
    request.state.request_id = "error-test-request"

    response = await unexpected_error(request, RuntimeError("private database details"))

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "error-test-request"
    assert json.loads(response.body) == {
        "detail": "Unexpected server error",
        "request_id": "error-test-request",
    }
