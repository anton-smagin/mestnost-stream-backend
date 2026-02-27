"""Tests for GET|POST /api/v1/me/* (user profile, history, likes)."""

import pytest
from httpx import AsyncClient

ME_URL = "/api/v1/me/"
HISTORY_URL = "/api/v1/me/history"
LIKES_URL = "/api/v1/me/likes"


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient, auth_headers, sample_user):
    """GET /me/ should return the authenticated user's profile."""
    resp = await client.get(ME_URL, headers=auth_headers)
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert body["meta"] is None

    data = body["data"]
    assert data["id"] == str(sample_user.id)
    assert data["email"] == sample_user.email
    assert data["display_name"] == sample_user.display_name
    assert "created_at" in data
    # password must not be exposed
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_get_profile_unauthorized(client: AsyncClient):
    """GET /me/ without a token should return 401/403."""
    resp = await client.get(ME_URL)
    assert resp.status_code in (401, 403)

    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None


# ---------------------------------------------------------------------------
# Listen history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_listen(client: AsyncClient, auth_headers, sample_artist):
    """POST /me/history should record a listen event and return it."""
    track = sample_artist._test_track1
    resp = await client.post(
        HISTORY_URL,
        json={"track_id": str(track.id)},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    data = body["data"]
    assert "id" in data
    assert "listened_at" in data
    assert data["track"]["id"] == str(track.id)


@pytest.mark.asyncio
async def test_record_listen_track_not_found(client: AsyncClient, auth_headers):
    """POST /me/history with unknown track_id should return 404."""
    import uuid

    resp = await client.post(
        HISTORY_URL,
        json={"track_id": str(uuid.uuid4())},
        headers=auth_headers,
    )
    assert resp.status_code == 404

    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None


@pytest.mark.asyncio
async def test_get_history(client: AsyncClient, auth_headers, sample_artist):
    """GET /me/history should include previously recorded listen events."""
    track = sample_artist._test_track1

    # Record a listen first
    await client.post(
        HISTORY_URL,
        json={"track_id": str(track.id)},
        headers=auth_headers,
    )

    resp = await client.get(HISTORY_URL, headers=auth_headers)
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert body["meta"] is not None
    assert body["meta"]["total"] >= 1

    track_ids = [h["track"]["id"] for h in body["data"]]
    assert str(track.id) in track_ids


# ---------------------------------------------------------------------------
# Likes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_like_track(client: AsyncClient, auth_headers, sample_artist):
    """POST /me/likes/{track_id} should like a track and return the Like entry."""
    track = sample_artist._test_track1
    resp = await client.post(f"{LIKES_URL}/{track.id}", headers=auth_headers)
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    data = body["data"]
    assert "id" in data
    assert data["track"]["id"] == str(track.id)


@pytest.mark.asyncio
async def test_like_track_idempotent(client: AsyncClient, auth_headers, sample_artist):
    """Liking the same track twice should not raise an error."""
    track = sample_artist._test_track1

    resp1 = await client.post(f"{LIKES_URL}/{track.id}", headers=auth_headers)
    assert resp1.status_code == 200

    resp2 = await client.post(f"{LIKES_URL}/{track.id}", headers=auth_headers)
    assert resp2.status_code == 200

    # Both responses should carry the same like ID
    assert resp1.json()["data"]["id"] == resp2.json()["data"]["id"]


@pytest.mark.asyncio
async def test_unlike_track(client: AsyncClient, auth_headers, sample_artist):
    """DELETE /me/likes/{track_id} should return 204 after liking."""
    track = sample_artist._test_track1

    # Like first
    await client.post(f"{LIKES_URL}/{track.id}", headers=auth_headers)

    resp = await client.delete(f"{LIKES_URL}/{track.id}", headers=auth_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_unlike_track_not_found(client: AsyncClient, auth_headers, sample_artist):
    """DELETE /me/likes/{track_id} when not liked should return 404."""
    track = sample_artist._test_track2
    resp = await client.delete(f"{LIKES_URL}/{track.id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_likes(client: AsyncClient, auth_headers, sample_artist):
    """GET /me/likes should return the list of liked tracks."""
    track = sample_artist._test_track1

    # Like the track first
    await client.post(f"{LIKES_URL}/{track.id}", headers=auth_headers)

    resp = await client.get(LIKES_URL, headers=auth_headers)
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert body["meta"] is not None
    assert body["meta"]["total"] >= 1

    track_ids = [like["track"]["id"] for like in body["data"]]
    assert str(track.id) in track_ids
