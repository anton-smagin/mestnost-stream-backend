"""Album service — retrieve album records with related data."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.album import Album


async def get_album(db: AsyncSession, album_id: uuid.UUID) -> Album | None:
    """Return an Album by ID with tracks (ordered by track_number) and artist eagerly loaded.

    Args:
        db: Async database session.
        album_id: The UUID primary key of the album.

    Returns:
        The Album ORM object with tracks and artist loaded, or None if not found.
    """
    album = await db.scalar(
        select(Album)
        .where(Album.id == album_id)
        .options(
            selectinload(Album.artist),
            selectinload(Album.tracks),
        )
    )
    if album is not None:
        album.tracks.sort(key=lambda t: t.track_number)
    return album
