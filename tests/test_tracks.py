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
    """GET /tracks/{id}/stream should return a URL in the standard envelope."""
    track = sample_artist._test_track1
    resp = await client.get(f"/api/v1/tracks/{track.id}/stream")
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert body["meta"] is None

    data = body["data"]
    assert "url" in data
    assert isinstance(data["url"], str)
    assert len(data["url"]) > 0
    # Mock URL should contain the track ID
    assert str(track.id) in data["url"]


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
