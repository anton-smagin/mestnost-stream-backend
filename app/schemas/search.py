"""Pydantic schemas for Search endpoint."""

from pydantic import BaseModel

from app.schemas.album import AlbumSummary
from app.schemas.artist import ArtistSummary
from app.schemas.track import TrackSummary


class SearchResults(BaseModel):
    artists: list[ArtistSummary]
    albums: list[AlbumSummary]
    tracks: list[TrackSummary]
