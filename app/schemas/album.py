"""Pydantic schemas for Album endpoints."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.track import TrackSummary


class AlbumSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    cover_image_url: str | None
    release_date: date


class AlbumDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    artist_id: UUID
    cover_image_url: str | None
    release_date: date
    tracks: list[TrackSummary]
    created_at: datetime
