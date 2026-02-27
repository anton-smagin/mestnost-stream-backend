"""Pydantic request schemas for admin endpoints."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class CreateArtistRequest(BaseModel):
    """Request body for POST /api/v1/admin/artists."""

    name: str
    slug: str
    bio: str | None = None
    image_url: str | None = None


class CreateAlbumRequest(BaseModel):
    """Request body for POST /api/v1/admin/albums."""

    title: str
    slug: str
    artist_id: UUID
    cover_image_url: str | None = None
    release_date: date
