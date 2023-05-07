import asyncio
from typing import Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from main import app
from config.database import Base, get_async_session
from config.settings import settings
from models.users import User
from views.auth import REFRESH_TOKEN_EXPIRE_DAYS, ACCESS_TOKEN_EXPIRE_MINUTES, create_jwt_token
from datetime import timedelta


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_session() -> AsyncSession:
    async_engine = create_async_engine(settings.test_database_url, echo=False)
    session = async_sessionmaker(async_engine, expire_on_commit=False)

    async with session() as s:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield s

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await async_engine.dispose()


@pytest_asyncio.fixture
async def async_client(async_session):
    app.dependency_overrides[get_async_session] = lambda: async_session
    async with AsyncClient(app=app, base_url='http://localhost/') as client:
        yield client


@pytest_asyncio.fixture
async def test_user(async_session) -> User:
    user = User(email="test@example.com", account_type="personal")
    user.set_password("password")
    async_session.add(user)
    await async_session.commit()
    return user


@pytest_asyncio.fixture
async def test_token(test_user):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return {
        "access_token": create_jwt_token(test_user.id, access_token_expires),
        "refresh_token": create_jwt_token(test_user.id, refresh_token_expires),
    }