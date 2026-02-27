"""Tests for /api/v1/playlists/* (playlist CRUD + track management)."""

import uuid

import pytest
from httpx import AsyncClient

from app.core.database import async_session
from app.models.user import User
from app.services.auth import create_access_token, hash_password

PLAYLISTS_URL = "/api/v1/playlists/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_second_user_headers() -> dict[str, str]:
    """Create a second user in the DB and return auth headers for them."""
    async with async_session() as session:
        user = User(
            email=f"other_{uuid.uuid4().hex[:8]}@test.example",
            display_name="Other User",
            password_hash=hash_password("otherpass123"),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_access_token(str(user.id))
        user_id = user.id

    return {"Authorization": f"Bearer {token}"}, user_id


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_playlist(client: AsyncClient, auth_headers):
    """POST /playlists/ should create a playlist and return its summary."""
    resp = await client.post(
        PLAYLISTS_URL,
        json={"name": "My New Playlist", "is_public": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    data = body["data"]
    assert data["name"] == "My New Playlist"
    assert data["is_public"] is False
    assert "id" in data
    assert "created_at" in data


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_playlists(client: AsyncClient, auth_headers):
    """GET /playlists/ should return only the authenticated user's playlists."""
    # Create one
    await client.post(
        PLAYLISTS_URL,
        json={"name": "Listed Playlist"},
        headers=auth_headers,
    )

    resp = await client.get(PLAYLISTS_URL, headers=auth_headers)
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert body["meta"]["total"] >= 1
    names = [p["name"] for p in body["data"]]
    assert "Listed Playlist" in names


# ---------------------------------------------------------------------------
# Get detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_playlist_with_tracks(client: AsyncClient, auth_headers, sample_artist):
    """GET /playlists/{id} should return playlist detail with tracks list."""
    track = sample_artist._test_track1

    # Create playlist
    create_resp = await client.post(
        PLAYLISTS_URL,
        json={"name": "Detail Playlist"},
        headers=auth_headers,
    )
    playlist_id = create_resp.json()["data"]["id"]

    # Add a track
    await client.post(
        f"{PLAYLISTS_URL}{playlist_id}/tracks",
        json={"track_id": str(track.id)},
        headers=auth_headers,
    )

    resp = await client.get(f"{PLAYLISTS_URL}{playlist_id}", headers=auth_headers)
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    data = body["data"]
    assert data["name"] == "Detail Playlist"
    assert "tracks" in data
    assert len(data["tracks"]) == 1
    assert data["tracks"][0]["track"]["id"] == str(track.id)
    assert data["tracks"][0]["position"] == 1


@pytest.mark.asyncio
async def test_get_playlist_not_found(client: AsyncClient, auth_headers):
    """GET /playlists/{id} with unknown ID should return 404."""
    resp = await client.get(f"{PLAYLISTS_URL}{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404

    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_playlist(client: AsyncClient, auth_headers):
    """PUT /playlists/{id} should update name and is_public."""
    create_resp = await client.post(
        PLAYLISTS_URL,
        json={"name": "Original Name"},
        headers=auth_headers,
    )
    playlist_id = create_resp.json()["data"]["id"]

    resp = await client.put(
        f"{PLAYLISTS_URL}{playlist_id}",
        json={"name": "Updated Name", "is_public": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    data = body["data"]
    assert data["name"] == "Updated Name"
    assert data["is_public"] is True


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_playlist(client: AsyncClient, auth_headers):
    """DELETE /playlists/{id} should return 204 and the playlist should be gone."""
    create_resp = await client.post(
        PLAYLISTS_URL,
        json={"name": "To Be Deleted"},
        headers=auth_headers,
    )
    playlist_id = create_resp.json()["data"]["id"]

    del_resp = await client.delete(
        f"{PLAYLISTS_URL}{playlist_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 204

    get_resp = await client.get(f"{PLAYLISTS_URL}{playlist_id}", headers=auth_headers)
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Add / Remove tracks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_track_to_playlist(client: AsyncClient, auth_headers, sample_artist):
    """POST /playlists/{id}/tracks should add a track with auto position."""
    track = sample_artist._test_track1

    create_resp = await client.post(
        PLAYLISTS_URL,
        json={"name": "Track Test Playlist"},
        headers=auth_headers,
    )
    playlist_id = create_resp.json()["data"]["id"]

    resp = await client.post(
        f"{PLAYLISTS_URL}{playlist_id}/tracks",
        json={"track_id": str(track.id)},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    data = body["data"]
    assert data["position"] == 1
    assert data["track"]["id"] == str(track.id)


@pytest.mark.asyncio
async def test_remove_track_from_playlist(client: AsyncClient, auth_headers, sample_artist):
    """DELETE /playlists/{id}/tracks/{track_id} should return 204."""
    track = sample_artist._test_track1

    create_resp = await client.post(
        PLAYLISTS_URL,
        json={"name": "Remove Track Playlist"},
        headers=auth_headers,
    )
    playlist_id = create_resp.json()["data"]["id"]

    await client.post(
        f"{PLAYLISTS_URL}{playlist_id}/tracks",
        json={"track_id": str(track.id)},
        headers=auth_headers,
    )

    resp = await client.delete(
        f"{PLAYLISTS_URL}{playlist_id}/tracks/{track.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 204

    # Playlist should now have no tracks
    get_resp = await client.get(f"{PLAYLISTS_URL}{playlist_id}", headers=auth_headers)
    assert get_resp.json()["data"]["tracks"] == []


@pytest.mark.asyncio
async def test_add_multiple_tracks_positions(client: AsyncClient, auth_headers, sample_artist):
    """Adding multiple tracks should assign sequential positions."""
    track1 = sample_artist._test_track1
    track2 = sample_artist._test_track2

    create_resp = await client.post(
        PLAYLISTS_URL,
        json={"name": "Multi Track Playlist"},
        headers=auth_headers,
    )
    playlist_id = create_resp.json()["data"]["id"]

    resp1 = await client.post(
        f"{PLAYLISTS_URL}{playlist_id}/tracks",
        json={"track_id": str(track1.id)},
        headers=auth_headers,
    )
    resp2 = await client.post(
        f"{PLAYLISTS_URL}{playlist_id}/tracks",
        json={"track_id": str(track2.id)},
        headers=auth_headers,
    )

    assert resp1.json()["data"]["position"] == 1
    assert resp2.json()["data"]["position"] == 2


# ---------------------------------------------------------------------------
# Ownership checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_playlist_ownership_check(client: AsyncClient, auth_headers):
    """Modifying another user's playlist should return 403."""
    # Create playlist as the primary test user
    create_resp = await client.post(
        PLAYLISTS_URL,
        json={"name": "Owner's Playlist"},
        headers=auth_headers,
    )
    playlist_id = create_resp.json()["data"]["id"]

    # Create a second user and try to update the first user's playlist
    other_headers, _ = await _create_second_user_headers()

    resp = await client.put(
        f"{PLAYLISTS_URL}{playlist_id}",
        json={"name": "Hijacked"},
        headers=other_headers,
    )
    assert resp.status_code == 403

    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None


@pytest.mark.asyncio
async def test_get_private_playlist_forbidden_for_other_user(client: AsyncClient, auth_headers):
    """GET /playlists/{id} on a private playlist belonging to another user should return 403."""
    # Create a private playlist as the primary test user
    create_resp = await client.post(
        PLAYLISTS_URL,
        json={"name": "Secret Playlist", "is_public": False},
        headers=auth_headers,
    )
    assert create_resp.status_code == 200
    playlist_id = create_resp.json()["data"]["id"]

    # A second user tries to read it — should be denied
    other_headers, _ = await _create_second_user_headers()

    resp = await client.get(f"{PLAYLISTS_URL}{playlist_id}", headers=other_headers)
    assert resp.status_code == 403

    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None


@pytest.mark.asyncio
async def test_get_public_playlist_accessible_by_other_user(client: AsyncClient, auth_headers):
    """GET /playlists/{id} on a public playlist should succeed for any authenticated user."""
    # Create a public playlist as the primary test user
    create_resp = await client.post(
        PLAYLISTS_URL,
        json={"name": "Public Playlist", "is_public": True},
        headers=auth_headers,
    )
    assert create_resp.status_code == 200
    playlist_id = create_resp.json()["data"]["id"]

    # A second user reads it — should succeed
    other_headers, _ = await _create_second_user_headers()

    resp = await client.get(f"{PLAYLISTS_URL}{playlist_id}", headers=other_headers)
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert body["data"]["name"] == "Public Playlist"


@pytest.mark.asyncio
async def test_add_same_track_twice_is_idempotent(client: AsyncClient, auth_headers, sample_artist):
    """POST /playlists/{id}/tracks with a duplicate track_id returns the existing entry."""
    track = sample_artist._test_track1

    create_resp = await client.post(
        PLAYLISTS_URL,
        json={"name": "Idempotent Track Test"},
        headers=auth_headers,
    )
    playlist_id = create_resp.json()["data"]["id"]

    # First add
    add1 = await client.post(
        f"{PLAYLISTS_URL}{playlist_id}/tracks",
        json={"track_id": str(track.id)},
        headers=auth_headers,
    )
    assert add1.status_code == 200
    assert add1.json()["data"]["position"] == 1

    # Second add of the same track — must return the same entry
    add2 = await client.post(
        f"{PLAYLISTS_URL}{playlist_id}/tracks",
        json={"track_id": str(track.id)},
        headers=auth_headers,
    )
    assert add2.status_code == 200
    assert add2.json()["data"]["id"] == add1.json()["data"]["id"]
    assert add2.json()["data"]["position"] == 1

    # Playlist must have exactly one track entry
    get_resp = await client.get(f"{PLAYLISTS_URL}{playlist_id}", headers=auth_headers)
    assert len(get_resp.json()["data"]["tracks"]) == 1
