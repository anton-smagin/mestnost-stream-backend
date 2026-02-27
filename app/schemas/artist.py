"""Pydantic schemas for Artist endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.album import AlbumSummary


class ArtistSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    image_url: str | None


class ArtistDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    bio: str | None
    image_url: str | None
    albums: list[AlbumSummary]
    created_at: datetime
