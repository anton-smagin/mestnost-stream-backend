"""Admin routes — create artists, albums, and upload tracks.

Mounted at /api/v1/admin in app.main.
All endpoints require a valid Bearer token (CurrentUserID dependency).
"""

import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.deps import DB, CurrentUserID
from app.core.response import ok
from app.schemas.admin import CreateAlbumRequest, CreateArtistRequest
from app.schemas.album import AlbumSummary
from app.schemas.artist import ArtistSummary
from app.schemas.track import TrackDetail
from app.services import admin as admin_service

router = APIRouter()

# ---------------------------------------------------------------------------
# Artists
# ---------------------------------------------------------------------------


@router.post("/artists")
async def create_artist_endpoint(
    body: CreateArtistRequest,
    db: DB,
    _user_id: CurrentUserID,
) -> dict:
    """Create a new artist record.

    Returns the created ArtistSummary in the standard envelope.
    """
    artist = await admin_service.create_artist(
        db=db,
        name=body.name,
        slug=body.slug,
        bio=body.bio,
        image_url=body.image_url,
    )
    return ok(ArtistSummary.model_validate(artist).model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Albums
# ---------------------------------------------------------------------------


@router.post("/albums")
async def create_album_endpoint(
    body: CreateAlbumRequest,
    db: DB,
    _user_id: CurrentUserID,
) -> dict:
    """Create a new album record linked to an existing artist.

    Returns the created AlbumSummary in the standard envelope.
    """
    album = await admin_service.create_album(
        db=db,
        title=body.title,
        slug=body.slug,
        artist_id=body.artist_id,
        cover_image_url=body.cover_image_url,
        release_date=body.release_date,
    )
    return ok(AlbumSummary.model_validate(album).model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Tracks
# ---------------------------------------------------------------------------


@router.post("/tracks")
async def upload_track_endpoint(
    db: DB,
    _user_id: CurrentUserID,
    title: str = Form(...),  # noqa: B008
    album_id: uuid.UUID = Form(...),  # noqa: B008
    track_number: int = Form(...),  # noqa: B008
    duration_seconds: int = Form(...),  # noqa: B008
    audio_file: UploadFile = File(...),  # noqa: B008
) -> dict:
    """Upload an audio file and create the track record.

    Accepts multipart/form-data with the following fields:
    - title (str): Display title of the track.
    - album_id (UUID): ID of the owning album.
    - track_number (int): 1-based position within the album.
    - duration_seconds (int): Track length in whole seconds.
    - audio_file (file): The audio file binary (FLAC recommended).

    Returns the created TrackDetail in the standard envelope.
    """
    if track_number < 1:
        raise HTTPException(status_code=422, detail="track_number must be >= 1")
    if duration_seconds < 1:
        raise HTTPException(status_code=422, detail="duration_seconds must be >= 1")

    audio_data = await audio_file.read()
    content_type = audio_file.content_type or "audio/flac"

    track = await admin_service.upload_track(
        db=db,
        title=title,
        album_id=album_id,
        track_number=track_number,
        duration_seconds=duration_seconds,
        audio_file_data=audio_data,
        audio_content_type=content_type,
    )
    return ok(TrackDetail.model_validate(track).model_dump(mode="json"))
