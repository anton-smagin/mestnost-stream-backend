"""Pydantic schemas for Track endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TrackSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    track_number: int
    duration_seconds: int


class TrackDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    track_number: int
    duration_seconds: int
    album_id: UUID
    file_key: str | None
    created_at: datetime


class StreamResponse(BaseModel):
    url: str
