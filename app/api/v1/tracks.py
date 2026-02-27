"""Track routes — GET /api/v1/tracks/{id} and GET /api/v1/tracks/{id}/stream.

Mounted at /api/v1/tracks in app.main.
"""

import uuid

from fastapi import APIRouter, HTTPException

from app.core.deps import DB
from app.core.response import ok
from app.schemas.track import TrackDetail
from app.services.track import get_stream_url, get_track

router = APIRouter()


@router.get("/{track_id}")
async def get_track_endpoint(track_id: uuid.UUID, db: DB) -> dict:
    """Return track detail, or 404 if not found."""
    track = await get_track(db=db, track_id=track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    return ok(TrackDetail.model_validate(track).model_dump(mode="json"))


@router.get("/{track_id}/stream")
async def get_stream_url_endpoint(track_id: uuid.UUID, db: DB) -> dict:
    """Return a presigned streaming URL for the track.

    Returns 404 if the track does not exist or has no audio file uploaded yet.
    Returns 503 (propagated from service) if R2 is temporarily unreachable.
    """
    url = await get_stream_url(db=db, track_id=track_id)
    if url is None:
        raise HTTPException(status_code=404, detail="Track not found or audio not available")
    return ok({"url": url})
