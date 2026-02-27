"""Track service — retrieve track records and generate stream URLs."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.track import Track


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

    Currently returns a mock URL.  Phase 3 will replace this with a real
    Cloudflare R2 presigned URL (expires in 1 hour).

    Args:
        db: Async database session.
        track_id: The UUID primary key of the track.

    Returns:
        A URL string if the track exists, otherwise None.
    """
    track = await get_track(db, track_id)
    if track is None:
        return None
    return f"https://mock-r2.example.com/stream/{track_id}"
