"""Tests for POST /api/v1/auth/register and POST /api/v1/auth/login."""

import uuid

import pytest
from httpx import AsyncClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def unique_email() -> str:
    """Generate a UUID-based email address to avoid DB conflicts across runs."""
    return f"user_{uuid.uuid4().hex[:12]}@test.example"


async def _register(client: AsyncClient, email: str, password: str = "StrongPass1!") -> dict:
    resp = await client.post(
        REGISTER_URL,
        json={"email": email, "password": password, "display_name": "Test User"},
    )
    return resp


# ---------------------------------------------------------------------------
# Register tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """POST /register should return 200 with the created user in the standard envelope."""
    email = unique_email()
    resp = await _register(client, email)

    assert resp.status_code == 200
    body = resp.json()

    # Standard envelope shape
    assert body["error"] is None
    assert body["data"] is not None

    user_data = body["data"]
    assert user_data["email"] == email
    assert user_data["display_name"] == "Test User"
    assert "id" in user_data
    assert "created_at" in user_data
    # password_hash must never be exposed
    assert "password_hash" not in user_data
    assert "password" not in user_data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Registering the same email twice should return 409."""
    email = unique_email()
    resp1 = await _register(client, email)
    assert resp1.status_code == 200

    resp2 = await _register(client, email)
    assert resp2.status_code == 409

    body = resp2.json()
    # Standard error envelope: {data: null, error: "...", meta: null}
    assert body["data"] is None
    assert body["error"] is not None
    assert "already registered" in body["error"]


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Registered user should be able to log in and receive a bearer token."""
    email = unique_email()
    password = "MySecret99!"

    reg = await _register(client, email, password)
    assert reg.status_code == 200

    resp = await client.post(LOGIN_URL, json={"email": email, "password": password})
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert body["data"] is not None

    token_data = body["data"]
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert len(token_data["access_token"]) > 10


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Login with incorrect password should return 401."""
    email = unique_email()
    reg = await _register(client, email, "CorrectPass1!")
    assert reg.status_code == 200

    resp = await client.post(LOGIN_URL, json={"email": email, "password": "WrongPass1!"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Login with an email that was never registered should return 401."""
    resp = await client.post(
        LOGIN_URL,
        json={"email": "nobody@nowhere.example", "password": "irrelevant"},
    )
    assert resp.status_code == 401
