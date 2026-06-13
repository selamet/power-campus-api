"""Shared pytest fixtures: an isolated database and an authenticated client.

Each test gets its own throwaway SQLite database (schema built from the ORM
metadata) and a FastAPI client whose ``get_session`` dependency is overridden to
use it, so tests never touch the development database.
"""

from collections.abc import AsyncIterator, Awaitable, Callable, Iterable

import app.models  # noqa: F401  -- registers every model on Base.metadata
import pytest
import pytest_asyncio
from app.apps.users.models import User, UserPermission, UserRole
from app.core.base import Base
from app.core.config import settings
from app.core.db import get_session
from app.core.security import hash_password
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

API = settings.api_v1_prefix

Headers = dict[str, str]


@pytest_asyncio.fixture
async def session_factory(tmp_path) -> AsyncIterator[async_sessionmaker]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def client(session_factory: async_sessionmaker) -> AsyncIterator[AsyncClient]:
    async def _override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(
    session_factory: async_sessionmaker,
) -> Callable[..., Awaitable[None]]:
    """Factory that inserts a user directly, bypassing the admin API."""

    async def _make(
        *,
        email: str,
        password: str,
        role: UserRole,
        permissions: Iterable[str] = (),
        must_change: bool = False,
        active: bool = True,
    ) -> None:
        async with session_factory() as session:
            session.add(
                User(
                    email=email,
                    password_hash=hash_password(password),
                    full_name="Test User",
                    role=role,
                    is_active=active,
                    must_change_password=must_change,
                    permissions=[UserPermission(permission=key) for key in permissions],
                )
            )
            await session.commit()

    return _make


@pytest_asyncio.fixture
async def admin(make_user: Callable[..., Awaitable[None]]) -> dict[str, str]:
    await make_user(email="admin@test.com", password="admin1234", role=UserRole.admin)
    return {"email": "admin@test.com", "password": "admin1234"}


@pytest.fixture
def login(client: AsyncClient) -> Callable[[str, str], Awaitable[Headers]]:
    """Factory returning bearer-auth headers for the given credentials."""

    async def _login(email: str, password: str) -> Headers:
        creds = {"email": email, "password": password}
        response = await client.post(f"{API}/auth/login", json=creds)
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['token']}"}

    return _login
