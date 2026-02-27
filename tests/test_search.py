"""Tests for GET /api/v1/search/?q={query}."""

import pytest
from httpx import AsyncClient

SEARCH_URL = "/api/v1/search/"


@pytest.mark.asyncio
async def test_search_by_artist_name(client: AsyncClient, sample_artist):
    """Searching for the artist name should return the artist in results."""
    resp = await client.get(SEARCH_URL, params={"q": "Test Artist"})
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    data = body["data"]
    assert "artists" in data
    assert "albums" in data
    assert "tracks" in data

    artist_ids = [a["id"] for a in data["artists"]]
    assert str(sample_artist.id) in artist_ids


@pytest.mark.asyncio
async def test_search_by_album_title(client: AsyncClient, sample_artist):
    """Searching for the album title should return the album in results."""
    resp = await client.get(SEARCH_URL, params={"q": "Test Album"})
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    data = body["data"]

    album_ids = [a["id"] for a in data["albums"]]
    assert str(sample_artist._test_album.id) in album_ids


@pytest.mark.asyncio
async def test_search_by_track_title(client: AsyncClient, sample_artist):
    """Searching for a track title should return the track in results."""
    resp = await client.get(SEARCH_URL, params={"q": "First Track"})
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    data = body["data"]

    track_ids = [t["id"] for t in data["tracks"]]
    assert str(sample_artist._test_track1.id) in track_ids


@pytest.mark.asyncio
async def test_search_empty_query(client: AsyncClient):
    """An empty q parameter should return empty result lists, not an error."""
    resp = await client.get(SEARCH_URL, params={"q": ""})
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    data = body["data"]
    assert data["artists"] == []
    assert data["albums"] == []
    assert data["tracks"] == []


@pytest.mark.asyncio
async def test_search_no_results(client: AsyncClient):
    """A query that matches nothing should return empty lists, not an error."""
    resp = await client.get(SEARCH_URL, params={"q": "zzz_no_match_xyzxyz"})
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    data = body["data"]
    assert data["artists"] == []
    assert data["albums"] == []
    assert data["tracks"] == []
