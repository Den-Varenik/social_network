import pytest
from sqlalchemy import select

from models.users import User

prefix = "/api/v1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "email, password, expected_status_code",
    [
        ("test@example.com", "password", 200),
        ("test@example.com", "wrong_password", 401),
        ("wrong_username", "password", 404),
    ],
)
async def test_create_token(async_client, test_user, email, password, expected_status_code) -> None:
    response = await async_client.post(
        f"{prefix}/auth/create",
        data={"username": email, "password": password}
    )
    assert response.status_code == expected_status_code


async def test_refresh_token(async_client, test_token) -> None:
    # Test successful token refresh
    response = await async_client.post(
        f"{prefix}/auth/refresh",
        json={"refresh_token": test_token['refresh_token']},
    )
    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # Test invalid token
    response = await async_client.post(
        f"{prefix}/auth/refresh",
        json={"refresh_token": "invalid_token"},
    )
    assert response.status_code == 401


async def test_verify_token(async_client, test_token) -> None:
    # Test successful token verification
    response = await async_client.post(
        f"{prefix}/auth/verify",
        headers={"Authorization": f"Bearer {test_token['access_token']}"},
    )
    assert response.status_code == 200

    # Test invalid token
    response = await async_client.post(
        f"{prefix}/auth/verify",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "email, password, account_type, expected_status_code",
    [
        ("test_new_user@example.com", "password", "personal", 200),
        ("test@example.com", "password", "personal", 400),
        ("test_email", "password", "personal", 422),
    ],
)
async def test_register_user(test_user, async_session, async_client, email, password, account_type, expected_status_code) -> None:
    response = await async_client.post(f"{prefix}/auth/register", json={
        "email": email,
        "password": password,
        "account_type": account_type
    })

    assert response.status_code == expected_status_code
    if expected_status_code == 200:
        assert response.json()["access_token"] is not None
        assert response.json()["refresh_token"] is not None

        result = await async_session.execute(select(User).where(User.email == email))
        created_user = result.scalar_one()

        assert created_user.email == email
        assert created_user.account_type.value == account_type
        assert created_user.check_password(password)
