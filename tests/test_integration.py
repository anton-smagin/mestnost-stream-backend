"""End-to-end integration tests for the Label Stream API.

Tests cover full user journeys, pagination correctness, auth boundaries, and
data integrity scenarios across multiple endpoints.  Each test uses real HTTP
calls via httpx.AsyncClient (ASGI transport) and a real (test) database.
"""

import uuid

import pytest
from httpx import AsyncClient

from app.core.database import async_session
from app.models.user import User
from app.services.auth import create_access_token, hash_password

# ---------------------------------------------------------------------------
# URL constants
# ---------------------------------------------------------------------------

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ARTISTS_URL = "/api/v1/artists/"
ALBUMS_URL = "/api/v1/albums/"
TRACKS_URL = "/api/v1/tracks/"
SEARCH_URL = "/api/v1/search/"
ME_URL = "/api/v1/me/"
HISTORY_URL = "/api/v1/me/history"
LIKES_URL = "/api/v1/me/likes"
PLAYLISTS_URL = "/api/v1/playlists/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unique_email() -> str:
    """Generate a collision-safe e-mail address for test isolation."""
    return f"integration_{uuid.uuid4().hex[:12]}@test.example"


async def _register_and_login(
    client: AsyncClient, email: str, password: str = "StrongPass1!"
) -> str:
    """Register a user and return a bearer token string."""
    reg = await client.post(
        REGISTER_URL,
        json={"email": email, "password": password, "display_name": "Integration User"},
    )
    assert reg.status_code == 200, reg.text

    login = await client.post(LOGIN_URL, json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()["data"]["access_token"]


def _auth(token: str) -> dict[str, str]:
    """Return Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Full user journey test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_user_journey(client: AsyncClient, sample_artist):
    """Walk through a complete user session from registration to playlist management."""

    # ── Step 1: Register a new user ────────────────────────────────────────
    email = _unique_email()
    reg_resp = await client.post(
        REGISTER_URL,
        json={"email": email, "password": "Journey99!", "display_name": "Journey User"},
    )
    assert reg_resp.status_code == 200
    reg_body = reg_resp.json()
    assert reg_body["error"] is None
    assert reg_body["data"]["email"] == email
    assert "password_hash" not in reg_body["data"]
    assert "password" not in reg_body["data"]

    # ── Step 2: Login and get token ─────────────────────────────────────────
    login_resp = await client.post(
        LOGIN_URL,
        json={"email": email, "password": "Journey99!"},
    )
    assert login_resp.status_code == 200
    login_body = login_resp.json()
    assert login_body["error"] is None
    token = login_body["data"]["access_token"]
    assert isinstance(token, str) and len(token) > 10
    assert login_body["data"]["token_type"] == "bearer"
    headers = _auth(token)

    # ── Step 3: Browse artists ──────────────────────────────────────────────
    artists_resp = await client.get(ARTISTS_URL)
    assert artists_resp.status_code == 200
    artists_body = artists_resp.json()
    assert artists_body["error"] is None
    assert isinstance(artists_body["data"], list)
    assert artists_body["meta"]["page"] == 1
    assert artists_body["meta"]["total"] >= 1

    artist_slugs = [a["slug"] for a in artists_body["data"]]
    assert sample_artist.slug in artist_slugs

    # ── Step 4: View artist detail ──────────────────────────────────────────
    artist_resp = await client.get(f"{ARTISTS_URL}{sample_artist.slug}")
    assert artist_resp.status_code == 200
    artist_body = artist_resp.json()
    assert artist_body["error"] is None
    assert artist_body["data"]["id"] == str(sample_artist.id)
    assert artist_body["data"]["name"] == "Test Artist"
    assert "albums" in artist_body["data"]
    assert len(artist_body["data"]["albums"]) >= 1

    # ── Step 5: View album detail ───────────────────────────────────────────
    album_id = str(sample_artist._test_album.id)
    album_resp = await client.get(f"{ALBUMS_URL}{album_id}")
    assert album_resp.status_code == 200
    album_body = album_resp.json()
    assert album_body["error"] is None
    assert album_body["data"]["id"] == album_id
    assert "tracks" in album_body["data"]
    assert len(album_body["data"]["tracks"]) >= 1

    # ── Step 6: Get stream URL ──────────────────────────────────────────────
    track_id = str(sample_artist._test_track1.id)
    stream_resp = await client.get(f"{TRACKS_URL}{track_id}/stream")
    assert stream_resp.status_code == 200
    stream_body = stream_resp.json()
    assert stream_body["error"] is None
    assert "url" in stream_body["data"]
    assert isinstance(stream_body["data"]["url"], str)
    assert len(stream_body["data"]["url"]) > 0

    # ── Step 7: Record a listen ─────────────────────────────────────────────
    listen_resp = await client.post(
        HISTORY_URL,
        json={"track_id": track_id},
        headers=headers,
    )
    assert listen_resp.status_code == 200
    listen_body = listen_resp.json()
    assert listen_body["error"] is None
    assert listen_body["data"]["track"]["id"] == track_id
    assert "listened_at" in listen_body["data"]

    # ── Step 8: Like a track ────────────────────────────────────────────────
    like_resp = await client.post(f"{LIKES_URL}/{track_id}", headers=headers)
    assert like_resp.status_code == 200
    like_body = like_resp.json()
    assert like_body["error"] is None
    like_id = like_body["data"]["id"]
    assert like_body["data"]["track"]["id"] == track_id

    # ── Step 9: Create a playlist ───────────────────────────────────────────
    pl_resp = await client.post(
        PLAYLISTS_URL,
        json={"name": "My Journey Playlist", "is_public": True},
        headers=headers,
    )
    assert pl_resp.status_code == 200
    pl_body = pl_resp.json()
    assert pl_body["error"] is None
    playlist_id = pl_body["data"]["id"]
    assert pl_body["data"]["name"] == "My Journey Playlist"
    assert pl_body["data"]["is_public"] is True

    # ── Step 10: Add track to playlist ─────────────────────────────────────
    add_resp = await client.post(
        f"{PLAYLISTS_URL}{playlist_id}/tracks",
        json={"track_id": track_id},
        headers=headers,
    )
    assert add_resp.status_code == 200
    add_body = add_resp.json()
    assert add_body["error"] is None
    assert add_body["data"]["position"] == 1
    assert add_body["data"]["track"]["id"] == track_id

    # ── Step 11: View playlist ──────────────────────────────────────────────
    view_resp = await client.get(f"{PLAYLISTS_URL}{playlist_id}", headers=headers)
    assert view_resp.status_code == 200
    view_body = view_resp.json()
    assert view_body["error"] is None
    assert view_body["data"]["name"] == "My Journey Playlist"
    assert len(view_body["data"]["tracks"]) == 1
    assert view_body["data"]["tracks"][0]["track"]["id"] == track_id

    # ── Step 12: Search for content ─────────────────────────────────────────
    search_resp = await client.get(SEARCH_URL, params={"q": "Test Artist"})
    assert search_resp.status_code == 200
    search_body = search_resp.json()
    assert search_body["error"] is None
    artist_ids = [a["id"] for a in search_body["data"]["artists"]]
    assert str(sample_artist.id) in artist_ids

    # ── Step 13: Verify history is recorded ────────────────────────────────
    history_resp = await client.get(HISTORY_URL, headers=headers)
    assert history_resp.status_code == 200
    history_body = history_resp.json()
    assert history_body["error"] is None
    assert history_body["meta"]["total"] >= 1
    listened_track_ids = [h["track"]["id"] for h in history_body["data"]]
    assert track_id in listened_track_ids

    # ── Step 14: Verify likes are recorded ─────────────────────────────────
    likes_resp = await client.get(LIKES_URL, headers=headers)
    assert likes_resp.status_code == 200
    likes_body = likes_resp.json()
    assert likes_body["error"] is None
    assert likes_body["meta"]["total"] >= 1
    liked_ids = [like["id"] for like in likes_body["data"]]
    assert like_id in liked_ids


# ---------------------------------------------------------------------------
# 2. Pagination tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pagination_artists_meta(client: AsyncClient, sample_artist):
    """GET /artists/?page=1&per_page=1 returns correct meta.page and meta.total."""
    resp = await client.get(ARTISTS_URL, params={"page": 1, "per_page": 1})
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert body["meta"]["page"] == 1
    assert body["meta"]["total"] >= 1
    assert len(body["data"]) == 1


@pytest.mark.asyncio
async def test_pagination_artists_beyond_total(client: AsyncClient, sample_artist):
    """Requesting a page beyond total returns an empty data list, not an error."""
    # First get the total so we know what page is definitively beyond it
    first = await client.get(ARTISTS_URL, params={"page": 1, "per_page": 100})
    total = first.json()["meta"]["total"]

    # Page 9999 will always be beyond the total
    resp = await client.get(ARTISTS_URL, params={"page": 9999, "per_page": 1})
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert body["data"] == []
    assert body["meta"]["total"] == total  # total stays accurate


@pytest.mark.asyncio
async def test_pagination_history_page_size(client: AsyncClient, auth_headers, sample_artist):
    """GET /me/history with per_page=1 returns exactly one entry per page."""
    track = sample_artist._test_track1

    # Record two listens
    await client.post(HISTORY_URL, json={"track_id": str(track.id)}, headers=auth_headers)
    await client.post(HISTORY_URL, json={"track_id": str(track.id)}, headers=auth_headers)

    resp = await client.get(HISTORY_URL, params={"page": 1, "per_page": 1}, headers=auth_headers)
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert len(body["data"]) == 1
    assert body["meta"]["page"] == 1
    assert body["meta"]["total"] >= 2


@pytest.mark.asyncio
async def test_pagination_likes_page_size(client: AsyncClient, auth_headers, sample_artist):
    """GET /me/likes with per_page=1 returns exactly one entry per page."""
    track1 = sample_artist._test_track1
    track2 = sample_artist._test_track2

    await client.post(f"{LIKES_URL}/{track1.id}", headers=auth_headers)
    await client.post(f"{LIKES_URL}/{track2.id}", headers=auth_headers)

    resp_p1 = await client.get(LIKES_URL, params={"page": 1, "per_page": 1}, headers=auth_headers)
    assert resp_p1.status_code == 200
    body_p1 = resp_p1.json()
    assert len(body_p1["data"]) == 1
    assert body_p1["meta"]["page"] == 1
    assert body_p1["meta"]["total"] >= 2

    resp_p2 = await client.get(LIKES_URL, params={"page": 2, "per_page": 1}, headers=auth_headers)
    assert resp_p2.status_code == 200
    body_p2 = resp_p2.json()
    assert len(body_p2["data"]) == 1
    assert body_p2["meta"]["page"] == 2

    # Page 1 and page 2 should contain different likes
    assert body_p1["data"][0]["id"] != body_p2["data"][0]["id"]


@pytest.mark.asyncio
async def test_pagination_playlists_meta(client: AsyncClient, auth_headers):
    """GET /playlists/ returns correct pagination meta."""
    # Create two playlists
    await client.post(PLAYLISTS_URL, json={"name": "Pagination PL 1"}, headers=auth_headers)
    await client.post(PLAYLISTS_URL, json={"name": "Pagination PL 2"}, headers=auth_headers)

    resp = await client.get(PLAYLISTS_URL, params={"page": 1, "per_page": 1}, headers=auth_headers)
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert len(body["data"]) == 1
    assert body["meta"]["page"] == 1
    assert body["meta"]["total"] >= 2


@pytest.mark.asyncio
async def test_pagination_playlists_beyond_total(client: AsyncClient, auth_headers):
    """Requesting playlists beyond total returns empty list."""
    resp = await client.get(
        PLAYLISTS_URL,
        params={"page": 9999, "per_page": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert body["data"] == []


# ---------------------------------------------------------------------------
# 3. Auth boundary tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_public_artists_no_token(client: AsyncClient, sample_artist):
    """GET /artists/ is accessible without authentication."""
    resp = await client.get(ARTISTS_URL)
    assert resp.status_code == 200
    assert resp.json()["error"] is None


@pytest.mark.asyncio
async def test_auth_public_artist_detail_no_token(client: AsyncClient, sample_artist):
    """GET /artists/{slug} is accessible without authentication."""
    resp = await client.get(f"{ARTISTS_URL}{sample_artist.slug}")
    assert resp.status_code == 200
    assert resp.json()["error"] is None


@pytest.mark.asyncio
async def test_auth_public_album_detail_no_token(client: AsyncClient, sample_artist):
    """GET /albums/{id} is accessible without authentication."""
    resp = await client.get(f"{ALBUMS_URL}{sample_artist._test_album.id}")
    assert resp.status_code == 200
    assert resp.json()["error"] is None


@pytest.mark.asyncio
async def test_auth_public_track_stream_no_token(client: AsyncClient, sample_artist):
    """GET /tracks/{id}/stream is accessible without authentication."""
    resp = await client.get(f"{TRACKS_URL}{sample_artist._test_track1.id}/stream")
    assert resp.status_code == 200
    assert resp.json()["error"] is None


@pytest.mark.asyncio
async def test_auth_public_search_no_token(client: AsyncClient):
    """GET /search/ is accessible without authentication."""
    resp = await client.get(SEARCH_URL, params={"q": "test"})
    assert resp.status_code == 200
    assert resp.json()["error"] is None


@pytest.mark.asyncio
async def test_auth_private_me_requires_token(client: AsyncClient):
    """GET /me/ without a token should return 401 or 403."""
    resp = await client.get(ME_URL)
    assert resp.status_code in (401, 403)
    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None


@pytest.mark.asyncio
async def test_auth_private_history_requires_token(client: AsyncClient):
    """GET /me/history without a token should return 401 or 403."""
    resp = await client.get(HISTORY_URL)
    assert resp.status_code in (401, 403)
    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None


@pytest.mark.asyncio
async def test_auth_private_likes_requires_token(client: AsyncClient):
    """GET /me/likes without a token should return 401 or 403."""
    resp = await client.get(LIKES_URL)
    assert resp.status_code in (401, 403)
    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None


@pytest.mark.asyncio
async def test_auth_private_playlists_requires_token(client: AsyncClient):
    """GET /playlists/ without a token should return 401 or 403."""
    resp = await client.get(PLAYLISTS_URL)
    assert resp.status_code in (401, 403)
    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None


@pytest.mark.asyncio
async def test_auth_private_post_history_requires_token(client: AsyncClient, sample_artist):
    """POST /me/history without a token should return 401 or 403."""
    track_id = str(sample_artist._test_track1.id)
    resp = await client.post(HISTORY_URL, json={"track_id": track_id})
    assert resp.status_code in (401, 403)
    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None


@pytest.mark.asyncio
async def test_auth_invalid_token_format(client: AsyncClient):
    """Requests with a malformed token should be rejected (401 or 403)."""
    bad_headers = {"Authorization": "Bearer not.a.valid.jwt.token"}
    resp = await client.get(ME_URL, headers=bad_headers)
    assert resp.status_code in (401, 403)
    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None


@pytest.mark.asyncio
async def test_auth_token_wrong_scheme(client: AsyncClient):
    """Providing a token with the wrong scheme should be rejected."""
    # Create a valid token but send it as 'Basic' instead of 'Bearer'
    async with async_session() as session:
        user = User(
            email=_unique_email(),
            display_name="Scheme Test User",
            password_hash=hash_password("pass123"),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        valid_token = create_access_token(str(user.id))
        user_id = user.id

    try:
        bad_headers = {"Authorization": f"Basic {valid_token}"}
        resp = await client.get(ME_URL, headers=bad_headers)
        assert resp.status_code in (401, 403)
    finally:
        from sqlalchemy import delete as sql_delete

        from app.models.user import User as UserModel

        async with async_session() as session:
            await session.execute(sql_delete(UserModel).where(UserModel.id == user_id))
            await session.commit()


# ---------------------------------------------------------------------------
# 4. Data integrity tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_data_integrity_like_unlike_toggle(client: AsyncClient, auth_headers, sample_artist):
    """Like then unlike a track — verify the like is added and then removed."""
    track = sample_artist._test_track1
    track_id = str(track.id)

    # Initially not liked — unlike should return 404
    not_liked = await client.delete(f"{LIKES_URL}/{track_id}", headers=auth_headers)
    assert not_liked.status_code == 404

    # Like the track
    like_resp = await client.post(f"{LIKES_URL}/{track_id}", headers=auth_headers)
    assert like_resp.status_code == 200
    like_id = like_resp.json()["data"]["id"]

    # Verify it appears in /me/likes
    get_resp = await client.get(LIKES_URL, headers=auth_headers)
    liked_ids = [like["id"] for like in get_resp.json()["data"]]
    assert like_id in liked_ids

    # Unlike the track
    unlike_resp = await client.delete(f"{LIKES_URL}/{track_id}", headers=auth_headers)
    assert unlike_resp.status_code == 204

    # Should no longer appear in /me/likes
    get_resp2 = await client.get(LIKES_URL, headers=auth_headers)
    liked_ids_after = [like["id"] for like in get_resp2.json()["data"]]
    assert like_id not in liked_ids_after

    # Unliking again should be 404
    unlike_again = await client.delete(f"{LIKES_URL}/{track_id}", headers=auth_headers)
    assert unlike_again.status_code == 404


@pytest.mark.asyncio
async def test_data_integrity_like_idempotent(client: AsyncClient, auth_headers, sample_artist):
    """Liking the same track twice returns the same like entry both times."""
    track = sample_artist._test_track1
    track_id = str(track.id)

    resp1 = await client.post(f"{LIKES_URL}/{track_id}", headers=auth_headers)
    assert resp1.status_code == 200
    id1 = resp1.json()["data"]["id"]

    resp2 = await client.post(f"{LIKES_URL}/{track_id}", headers=auth_headers)
    assert resp2.status_code == 200
    id2 = resp2.json()["data"]["id"]

    assert id1 == id2, "Idempotent like should return the same like entry"


@pytest.mark.asyncio
async def test_data_integrity_add_same_track_to_playlist_twice(
    client: AsyncClient, auth_headers, sample_artist
):
    """Adding the same track twice is idempotent — the second call returns the existing entry.

    The playlist service deduplicates tracks: if a track is already present in
    a playlist, the add call returns the existing PlaylistTrack entry (same id
    and position) rather than creating a second entry.
    """
    track = sample_artist._test_track1
    track_id = str(track.id)

    # Create a fresh playlist
    pl_resp = await client.post(
        PLAYLISTS_URL,
        json={"name": "Duplicate Track Test"},
        headers=auth_headers,
    )
    playlist_id = pl_resp.json()["data"]["id"]

    # Add the track once — should succeed with position 1
    add1 = await client.post(
        f"{PLAYLISTS_URL}{playlist_id}/tracks",
        json={"track_id": track_id},
        headers=auth_headers,
    )
    assert add1.status_code == 200
    assert add1.json()["data"]["position"] == 1

    # Add the same track again — service returns the existing entry (idempotent)
    add2 = await client.post(
        f"{PLAYLISTS_URL}{playlist_id}/tracks",
        json={"track_id": track_id},
        headers=auth_headers,
    )
    assert add2.status_code == 200
    assert add2.json()["data"]["position"] == 1

    # Both responses reference the same playlist_track entry
    assert add1.json()["data"]["id"] == add2.json()["data"]["id"]

    # Playlist should have exactly one entry for the track
    view = await client.get(f"{PLAYLISTS_URL}{playlist_id}", headers=auth_headers)
    tracks_in_playlist = view.json()["data"]["tracks"]
    assert len(tracks_in_playlist) == 1
    track_entries = [t for t in tracks_in_playlist if t["track"]["id"] == track_id]
    assert len(track_entries) == 1, "Duplicate add must not create a second entry"
    assert track_entries[0]["position"] == 1


@pytest.mark.asyncio
async def test_data_integrity_playlist_position_compaction(
    client: AsyncClient, auth_headers, sample_artist
):
    """After removing a track from the middle, remaining tracks have compacted positions."""
    track1 = sample_artist._test_track1
    track2 = sample_artist._test_track2

    # Create playlist and add both tracks
    pl_resp = await client.post(
        PLAYLISTS_URL,
        json={"name": "Position Compaction Test"},
        headers=auth_headers,
    )
    playlist_id = pl_resp.json()["data"]["id"]

    add1 = await client.post(
        f"{PLAYLISTS_URL}{playlist_id}/tracks",
        json={"track_id": str(track1.id)},
        headers=auth_headers,
    )
    add2 = await client.post(
        f"{PLAYLISTS_URL}{playlist_id}/tracks",
        json={"track_id": str(track2.id)},
        headers=auth_headers,
    )
    assert add1.json()["data"]["position"] == 1
    assert add2.json()["data"]["position"] == 2

    # Remove the first track (position 1)
    del_resp = await client.delete(
        f"{PLAYLISTS_URL}{playlist_id}/tracks/{track1.id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 204

    # View the playlist — track2 should now be at position 1
    view = await client.get(f"{PLAYLISTS_URL}{playlist_id}", headers=auth_headers)
    assert view.status_code == 200
    remaining = view.json()["data"]["tracks"]
    assert len(remaining) == 1
    assert remaining[0]["track"]["id"] == str(track2.id)
    assert remaining[0]["position"] == 1


@pytest.mark.asyncio
async def test_data_integrity_history_records_multiple_listens(
    client: AsyncClient, auth_headers, sample_artist
):
    """Listening to the same track multiple times creates multiple history entries."""
    track = sample_artist._test_track1
    track_id = str(track.id)

    listen1 = await client.post(HISTORY_URL, json={"track_id": track_id}, headers=auth_headers)
    listen2 = await client.post(HISTORY_URL, json={"track_id": track_id}, headers=auth_headers)
    assert listen1.status_code == 200
    assert listen2.status_code == 200

    # The two listen events must have distinct IDs
    id1 = listen1.json()["data"]["id"]
    id2 = listen2.json()["data"]["id"]
    assert id1 != id2, "Each listen event should be a separate history entry"

    # Both should appear in history
    history_resp = await client.get(HISTORY_URL, headers=auth_headers)
    history_ids = [h["id"] for h in history_resp.json()["data"]]
    assert id1 in history_ids
    assert id2 in history_ids


@pytest.mark.asyncio
async def test_data_integrity_user_isolation(client: AsyncClient, sample_artist):
    """One user's playlists and likes are not visible to another user."""
    track = sample_artist._test_track1

    # Create two separate users
    email_a = _unique_email()
    email_b = _unique_email()
    token_a = await _register_and_login(client, email_a)
    token_b = await _register_and_login(client, email_b)
    headers_a = _auth(token_a)
    headers_b = _auth(token_b)

    # User A likes the track and creates a playlist
    await client.post(f"{LIKES_URL}/{track.id}", headers=headers_a)
    pl_resp = await client.post(
        PLAYLISTS_URL,
        json={"name": "User A Private Playlist"},
        headers=headers_a,
    )
    playlist_id = pl_resp.json()["data"]["id"]

    # User B's likes list should be empty
    likes_b = await client.get(LIKES_URL, headers=headers_b)
    assert likes_b.json()["meta"]["total"] == 0

    # User B's playlists list should be empty
    pl_b = await client.get(PLAYLISTS_URL, headers=headers_b)
    pl_ids_b = [p["id"] for p in pl_b.json()["data"]]
    assert playlist_id not in pl_ids_b


@pytest.mark.asyncio
async def test_data_integrity_standard_response_envelope(client: AsyncClient, sample_artist):
    """Every endpoint must return the standard {data, error, meta} envelope."""
    endpoints = [
        (ARTISTS_URL, None),
        (f"{ARTISTS_URL}{sample_artist.slug}", None),
        (f"{ALBUMS_URL}{sample_artist._test_album.id}", None),
        (f"{TRACKS_URL}{sample_artist._test_track1.id}", None),
        (f"{TRACKS_URL}{sample_artist._test_track1.id}/stream", None),
        (SEARCH_URL + "?q=test", None),
    ]

    for url, _param in endpoints:
        resp = await client.get(url)
        assert resp.status_code == 200, f"Unexpected status for {url}: {resp.status_code}"
        body = resp.json()
        assert "data" in body, f"Missing 'data' key in response from {url}"
        assert "error" in body, f"Missing 'error' key in response from {url}"
        assert "meta" in body, f"Missing 'meta' key in response from {url}"
        assert body["error"] is None, f"Unexpected error from {url}: {body['error']}"
