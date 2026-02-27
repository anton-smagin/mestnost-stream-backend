"""Track service — retrieve track records and generate stream URLs."""

import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.track import Track
from app.services import storage

logger = logging.getLogger(__name__)


async def get_track(db: AsyncSession, track_id: uuid.UUID) -> Track | None:
    """Return a Track by ID, or None if not found.

    Args:
        db: Async database session.
        track_id: The UUID primary key of the track.

    Returns:
        The Track ORM object, or None.
    """
    return await db.scalar(select(Track).where(Track.id == track_id))


async def get_stream_url(db: AsyncSession, track_id: uuid.UUID) -> str | None:
    """Return a presigned streaming URL for the given track, or None if not found.

    Fetches the track record to obtain its R2 file_key, then delegates to the
    storage service to generate a presigned URL with a 1-hour expiry.

    Args:
        db: Async database session.
        track_id: The UUID primary key of the track.

    Returns:
        A presigned URL string if the track exists and has a file_key, else None.

    Raises:
        HTTPException: 503 if the R2 presigned-URL generation fails.
        HTTPException: 404 (via None return path) if the track has no file_key.
    """
    track = await get_track(db, track_id)
    if track is None:
        return None

    if not track.file_key:
        # Track exists in DB but has no uploaded audio file yet.
        return None

    try:
        url = await storage.get_presigned_url(track.file_key)
    except Exception as exc:
        logger.exception("R2 presigned URL generation failed for track %s", track_id)
        raise HTTPException(
            status_code=503,
            detail="Audio stream temporarily unavailable. Please try again later.",
        ) from exc

    return url
