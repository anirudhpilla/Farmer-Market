from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from app.database import get_db_session
from app.main import app


async def test_health_check_reports_database_connection() -> None:
    fake_session = AsyncMock()

    async def override_session() -> AsyncIterator[AsyncMock]:
        yield fake_session

    app.dependency_overrides[get_db_session] = override_session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}
    fake_session.execute.assert_awaited_once()
