"""Tests for GET /api/v1/tracks/{id} and GET /api/v1/tracks/{id}/stream."""

import uuid

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Get track
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_track(client: AsyncClient, sample_artist):
    """GET /tracks/{id} should return track detail in the standard envelope."""
    track = sample_artist._test_track1
    resp = await client.get(f"/api/v1/tracks/{track.id}")
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert body["meta"] is None

    data = body["data"]
    assert data["id"] == str(track.id)
    assert data["title"] == "First Track"
    assert data["slug"] == track.slug
    assert data["track_number"] == 1
    assert data["duration_seconds"] == 210
    assert data["album_id"] == str(sample_artist._test_album.id)
    assert data["file_key"] == track.file_key
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_track_not_found(client: AsyncClient):
    """GET /tracks/{id} with unknown UUID should return 404 standard envelope."""
    missing_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/tracks/{missing_id}")
    assert resp.status_code == 404

    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None
    assert "not found" in body["error"].lower()
    assert body["meta"] is None


@pytest.mark.asyncio
async def test_get_track_invalid_uuid(client: AsyncClient):
    """GET /tracks/not-a-uuid should return 422 validation error."""
    resp = await client.get("/api/v1/tracks/not-a-uuid")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Stream URL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_stream_url(client: AsyncClient, sample_artist):
    """GET /tracks/{id}/stream returns a presigned URL in the standard envelope.

    In development / test (r2_endpoint is empty) the storage service returns a
    mock URL of the form https://mock-r2.dev/{file_key}?expires=3600.
    We verify the response shape and that the URL is a non-empty string.
    """
    track = sample_artist._test_track1
    resp = await client.get(f"/api/v1/tracks/{track.id}/stream")
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert body["meta"] is None

    data = body["data"]
    assert "url" in data
    url = data["url"]
    assert isinstance(url, str)
    assert len(url) > 0
    # In mock mode the URL embeds the file_key which contains the track slug
    assert track.slug.split("-")[0] in url or "mock-r2" in url


@pytest.mark.asyncio
async def test_get_stream_url_not_found(client: AsyncClient):
    """GET /tracks/{id}/stream with unknown UUID should return 404 standard envelope."""
    missing_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/tracks/{missing_id}/stream")
    assert resp.status_code == 404

    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None
    assert "not found" in body["error"].lower()
    assert body["meta"] is None


@pytest.mark.asyncio
async def test_get_stream_url_no_file_key(client: AsyncClient, db_session):
    """GET /tracks/{id}/stream for a track with no file_key returns 404."""
    import datetime

    from app.core.database import async_session
    from app.models.album import Album
    from app.models.artist import Artist
    from app.models.track import Track

    artist_id = uuid.uuid4()
    album_id = uuid.uuid4()
    track_id = uuid.uuid4()

    async with async_session() as session:
        session.add(Artist(id=artist_id, name="No File Artist", slug=f"nf-{artist_id.hex[:8]}"))
        await session.flush()
        session.add(
            Album(
                id=album_id,
                title="No File Album",
                slug=f"nf-{album_id.hex[:8]}",
                artist_id=artist_id,
                release_date=datetime.date(2024, 1, 1),
            )
        )
        await session.flush()
        session.add(
            Track(
                id=track_id,
                title="No File Track",
                slug=f"nf-{track_id.hex[:8]}",
                album_id=album_id,
                track_number=1,
                duration_seconds=100,
                file_key=None,
            )
        )
        await session.commit()

    resp = await client.get(f"/api/v1/tracks/{track_id}/stream")
    assert resp.status_code == 404
    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None

    # Cleanup
    async with async_session() as session:
        from sqlalchemy import delete

        await session.execute(delete(Artist).where(Artist.id == artist_id))
        await session.commit()
