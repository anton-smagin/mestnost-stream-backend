"""Tests for GET /api/v1/albums/{id}."""

import uuid

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Get album
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_album_with_tracks(client: AsyncClient, sample_artist):
    """GET /albums/{id} should return album detail including tracks ordered by track_number."""
    album = sample_artist._test_album
    resp = await client.get(f"/api/v1/albums/{album.id}")
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert body["meta"] is None

    data = body["data"]
    assert data["id"] == str(album.id)
    assert data["title"] == "Test Album"
    assert data["slug"] == album.slug
    assert data["artist_id"] == str(sample_artist.id)
    assert data["cover_image_url"] == "https://example.com/cover.jpg"
    assert "release_date" in data
    assert "created_at" in data

    # Must include tracks list
    assert "tracks" in data
    assert isinstance(data["tracks"], list)
    assert len(data["tracks"]) == 2

    # Tracks must be ordered by track_number
    track_numbers = [t["track_number"] for t in data["tracks"]]
    assert track_numbers == sorted(track_numbers)

    # Verify track shape
    first_track = data["tracks"][0]
    assert first_track["title"] == "First Track"
    assert first_track["track_number"] == 1
    assert first_track["duration_seconds"] == 210
    assert "id" in first_track
    assert "slug" in first_track


@pytest.mark.asyncio
async def test_get_album_not_found(client: AsyncClient):
    """GET /albums/{id} with unknown UUID should return 404 standard envelope."""
    missing_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/albums/{missing_id}")
    assert resp.status_code == 404

    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None
    assert "not found" in body["error"].lower()
    assert body["meta"] is None


@pytest.mark.asyncio
async def test_get_album_invalid_uuid(client: AsyncClient):
    """GET /albums/not-a-uuid should return 422 validation error."""
    resp = await client.get("/api/v1/albums/not-a-uuid")
    assert resp.status_code == 422
