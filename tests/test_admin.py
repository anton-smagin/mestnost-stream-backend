"""Tests for POST /api/v1/admin/artists, /albums, and /tracks."""

import io
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.core.database import async_session
from app.models.album import Album
from app.models.artist import Artist
from app.models.track import Track

ADMIN_ARTISTS = "/api/v1/admin/artists"
ADMIN_ALBUMS = "/api/v1/admin/albums"
ADMIN_TRACKS = "/api/v1/admin/tracks"


# ---------------------------------------------------------------------------
# Helper: small synthetic FLAC-like bytes for multipart uploads
# ---------------------------------------------------------------------------

FAKE_AUDIO = b"fLaC" + b"\x00" * 64  # 68 bytes — not a valid FLAC but enough for tests


# ---------------------------------------------------------------------------
# Artist creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_artist(client: AsyncClient, auth_headers: dict):
    """POST /admin/artists creates an artist and returns ArtistSummary envelope."""
    slug = f"test-new-artist-{uuid.uuid4().hex[:8]}"
    payload = {
        "name": "New Artist",
        "slug": slug,
        "bio": "A short biography.",
        "image_url": "https://example.com/img.jpg",
    }
    resp = await client.post(ADMIN_ARTISTS, json=payload, headers=auth_headers)
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["error"] is None

    data = body["data"]
    assert data["name"] == "New Artist"
    assert data["slug"] == slug
    assert "id" in data
    artist_id = uuid.UUID(data["id"])

    # Cleanup
    async with async_session() as session:
        await session.execute(delete(Artist).where(Artist.id == artist_id))
        await session.commit()


@pytest.mark.asyncio
async def test_create_artist_duplicate_slug(client: AsyncClient, auth_headers: dict, sample_artist):
    """POST /admin/artists with a duplicate slug returns 409."""
    payload = {
        "name": "Duplicate",
        "slug": sample_artist.slug,  # already exists
    }
    resp = await client.post(ADMIN_ARTISTS, json=payload, headers=auth_headers)
    assert resp.status_code == 409

    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None


@pytest.mark.asyncio
async def test_create_artist_unauthorized(client: AsyncClient):
    """POST /admin/artists without auth returns 401/403."""
    payload = {"name": "No Auth Artist", "slug": "no-auth-artist"}
    resp = await client.post(ADMIN_ARTISTS, json=payload)
    assert resp.status_code in (401, 403)

    body = resp.json()
    assert body["data"] is None


# ---------------------------------------------------------------------------
# Album creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_album(client: AsyncClient, auth_headers: dict, sample_artist):
    """POST /admin/albums creates an album and returns AlbumSummary envelope."""
    slug = f"new-album-{uuid.uuid4().hex[:8]}"
    payload = {
        "title": "New Album",
        "slug": slug,
        "artist_id": str(sample_artist.id),
        "cover_image_url": None,
        "release_date": "2025-06-01",
    }
    resp = await client.post(ADMIN_ALBUMS, json=payload, headers=auth_headers)
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["error"] is None

    data = body["data"]
    assert data["title"] == "New Album"
    assert data["slug"] == slug
    assert data["release_date"] == "2025-06-01"
    assert "id" in data
    album_id = uuid.UUID(data["id"])

    # Cleanup
    async with async_session() as session:
        await session.execute(delete(Album).where(Album.id == album_id))
        await session.commit()


@pytest.mark.asyncio
async def test_create_album_artist_not_found(client: AsyncClient, auth_headers: dict):
    """POST /admin/albums with non-existent artist_id returns 404."""
    payload = {
        "title": "Ghost Album",
        "slug": "ghost-album",
        "artist_id": str(uuid.uuid4()),
        "release_date": "2025-01-01",
    }
    resp = await client.post(ADMIN_ALBUMS, json=payload, headers=auth_headers)
    assert resp.status_code == 404

    body = resp.json()
    assert body["data"] is None
    assert "not found" in body["error"].lower()


@pytest.mark.asyncio
async def test_create_album_unauthorized(client: AsyncClient, sample_artist):
    """POST /admin/albums without auth returns 401/403."""
    payload = {
        "title": "No Auth Album",
        "slug": "no-auth-album",
        "artist_id": str(sample_artist.id),
        "release_date": "2025-01-01",
    }
    resp = await client.post(ADMIN_ALBUMS, json=payload)
    assert resp.status_code in (401, 403)

    body = resp.json()
    assert body["data"] is None


# ---------------------------------------------------------------------------
# Track upload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_track(client: AsyncClient, auth_headers: dict, sample_artist):
    """POST /admin/tracks uploads audio and returns TrackDetail envelope."""
    album = sample_artist._test_album

    form_data = {
        "title": "Brand New Track",
        "album_id": str(album.id),
        "track_number": "10",
        "duration_seconds": "180",
    }
    files = {"audio_file": ("track.flac", io.BytesIO(FAKE_AUDIO), "audio/flac")}

    resp = await client.post(ADMIN_TRACKS, data=form_data, files=files, headers=auth_headers)
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["error"] is None

    data = body["data"]
    assert data["title"] == "Brand New Track"
    assert data["track_number"] == 10
    assert data["duration_seconds"] == 180
    assert data["album_id"] == str(album.id)
    # In mock mode a file_key must be stored
    assert data["file_key"] is not None
    assert "brand-new-track" in data["file_key"]
    assert "id" in data

    # Cleanup
    track_id = uuid.UUID(data["id"])
    async with async_session() as session:
        await session.execute(delete(Track).where(Track.id == track_id))
        await session.commit()


@pytest.mark.asyncio
async def test_upload_track_album_not_found(client: AsyncClient, auth_headers: dict):
    """POST /admin/tracks with non-existent album_id returns 404."""
    form_data = {
        "title": "Ghost Track",
        "album_id": str(uuid.uuid4()),
        "track_number": "1",
        "duration_seconds": "120",
    }
    files = {"audio_file": ("track.flac", io.BytesIO(FAKE_AUDIO), "audio/flac")}

    resp = await client.post(ADMIN_TRACKS, data=form_data, files=files, headers=auth_headers)
    assert resp.status_code == 404

    body = resp.json()
    assert body["data"] is None
    assert "not found" in body["error"].lower()


@pytest.mark.asyncio
async def test_upload_track_unauthorized(client: AsyncClient, sample_artist):
    """POST /admin/tracks without auth returns 401/403."""
    album = sample_artist._test_album
    form_data = {
        "title": "Unauth Track",
        "album_id": str(album.id),
        "track_number": "1",
        "duration_seconds": "120",
    }
    files = {"audio_file": ("track.flac", io.BytesIO(FAKE_AUDIO), "audio/flac")}

    resp = await client.post(ADMIN_TRACKS, data=form_data, files=files)
    assert resp.status_code in (401, 403)

    body = resp.json()
    assert body["data"] is None


@pytest.mark.asyncio
async def test_upload_track_duplicate_slug(client: AsyncClient, auth_headers: dict, sample_artist):
    """POST /admin/tracks with a duplicate title (same slug) returns 409.

    We first upload a track with a known title, then attempt to upload a second
    track with the exact same title on the same album — the service must reject
    the second upload with 409 because the slug would collide.
    """
    album = sample_artist._test_album
    unique_title = f"Collision Track {uuid.uuid4().hex[:6]}"

    # First upload — must succeed
    form_first = {
        "title": unique_title,
        "album_id": str(album.id),
        "track_number": "50",
        "duration_seconds": "120",
    }
    files_first = {"audio_file": ("a.flac", io.BytesIO(FAKE_AUDIO), "audio/flac")}
    resp_first = await client.post(
        ADMIN_TRACKS, data=form_first, files=files_first, headers=auth_headers
    )
    assert resp_first.status_code == 200, resp_first.text
    track_id = uuid.UUID(resp_first.json()["data"]["id"])

    # Second upload with same title — must be rejected
    form_second = {
        "title": unique_title,
        "album_id": str(album.id),
        "track_number": "51",
        "duration_seconds": "130",
    }
    files_second = {"audio_file": ("b.flac", io.BytesIO(FAKE_AUDIO), "audio/flac")}
    resp_second = await client.post(
        ADMIN_TRACKS, data=form_second, files=files_second, headers=auth_headers
    )
    assert resp_second.status_code == 409

    body = resp_second.json()
    assert body["data"] is None
    assert body["error"] is not None

    # Cleanup the first track
    async with async_session() as session:
        await session.execute(delete(Track).where(Track.id == track_id))
        await session.commit()
