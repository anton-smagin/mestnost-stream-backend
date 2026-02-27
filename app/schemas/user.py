"""Pydantic schemas for User / Me endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.track import TrackSummary


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    created_at: datetime


class ListenHistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    track: TrackSummary
    listened_at: datetime


class LikeEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    track: TrackSummary
    created_at: datetime


class RecordListenRequest(BaseModel):
    track_id: UUID
