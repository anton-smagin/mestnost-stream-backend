"""Tests for GET /api/v1/artists and GET /api/v1/artists/{slug}."""

import pytest
from httpx import AsyncClient

LIST_URL = "/api/v1/artists/"


# ---------------------------------------------------------------------------
# List artists
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_artists_empty(client: AsyncClient):
    """GET /artists/ with no data should return an empty list with correct meta."""
    resp = await client.get(LIST_URL)
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert isinstance(body["data"], list)
    assert "meta" in body
    assert body["meta"]["page"] == 1
    assert body["meta"]["total"] >= 0


@pytest.mark.asyncio
async def test_list_artists(client: AsyncClient, sample_artist):
    """GET /artists/ should return paginated artists with standard envelope."""
    resp = await client.get(LIST_URL)
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert isinstance(body["data"], list)
    assert body["meta"]["page"] == 1
    assert body["meta"]["total"] >= 1

    # Verify shape of at least one artist
    artist_slugs = [a["slug"] for a in body["data"]]
    assert sample_artist.slug in artist_slugs

    # Find our fixture artist
    fixture_artist = next(a for a in body["data"] if a["slug"] == sample_artist.slug)
    assert fixture_artist["name"] == "Test Artist"
    assert fixture_artist["image_url"] == "https://example.com/artist.jpg"
    assert "id" in fixture_artist
    # ArtistSummary should NOT include bio or albums
    assert "bio" not in fixture_artist
    assert "albums" not in fixture_artist


@pytest.mark.asyncio
async def test_list_artists_pagination(client: AsyncClient, sample_artist):
    """GET /artists/?page=1&per_page=1 should respect pagination parameters."""
    resp = await client.get(LIST_URL, params={"page": 1, "per_page": 1})
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert len(body["data"]) <= 1
    assert body["meta"]["page"] == 1


# ---------------------------------------------------------------------------
# Get artist by slug
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_artist_by_slug(client: AsyncClient, sample_artist):
    """GET /artists/{slug} should return artist detail with albums list."""
    resp = await client.get(f"/api/v1/artists/{sample_artist.slug}")
    assert resp.status_code == 200

    body = resp.json()
    assert body["error"] is None
    assert body["meta"] is None

    artist = body["data"]
    assert artist["id"] == str(sample_artist.id)
    assert artist["name"] == "Test Artist"
    assert artist["slug"] == sample_artist.slug
    assert artist["bio"] == "A test artist bio."
    assert artist["image_url"] == "https://example.com/artist.jpg"
    assert "created_at" in artist

    # Must include albums list
    assert "albums" in artist
    assert isinstance(artist["albums"], list)
    assert len(artist["albums"]) >= 1

    album = artist["albums"][0]
    assert album["title"] == "Test Album"
    assert album["slug"] == sample_artist._test_album.slug
    assert "id" in album
    assert "release_date" in album


@pytest.mark.asyncio
async def test_get_artist_not_found(client: AsyncClient):
    """GET /artists/{slug} with unknown slug should return 404 standard envelope."""
    resp = await client.get("/api/v1/artists/does-not-exist-xyz")
    assert resp.status_code == 404

    body = resp.json()
    assert body["data"] is None
    assert body["error"] is not None
    assert "not found" in body["error"].lower()
    assert body["meta"] is None
