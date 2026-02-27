"""Pydantic schemas for Playlist endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.track import TrackSummary


class PlaylistSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    is_public: bool
    created_at: datetime


class PlaylistTrackEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    track: TrackSummary
    position: int


class PlaylistDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    is_public: bool
    # ORM relationship is named playlist_tracks; expose as "tracks" in the API
    tracks: list[PlaylistTrackEntry] = Field(validation_alias="playlist_tracks")
    created_at: datetime


class CreatePlaylistRequest(BaseModel):
    name: str
    is_public: bool = False


class UpdatePlaylistRequest(BaseModel):
    name: str | None = None
    is_public: bool | None = None


class AddTrackRequest(BaseModel):
    track_id: UUID
