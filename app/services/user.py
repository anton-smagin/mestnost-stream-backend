"""User service — profile, listen history, and likes."""

import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.like import Like
from app.models.listen_history import ListenHistory
from app.models.track import Track
from app.models.user import User


async def get_user_profile(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Return a User by primary key, or None if not found.

    Args:
        db: Async database session.
        user_id: The UUID primary key of the user.

    Returns:
        The User ORM object, or None.
    """
    return await db.scalar(select(User).where(User.id == user_id))


async def get_listen_history(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[ListenHistory], int]:
    """Return a paginated listen history for a user ordered by listened_at DESC.

    Args:
        db: Async database session.
        user_id: The UUID of the user whose history is being fetched.
        page: 1-based page number.
        per_page: Number of entries per page.

    Returns:
        Tuple of (history list, total count).
    """
    offset = (page - 1) * per_page

    total: int = (
        await db.scalar(
            select(func.count()).select_from(ListenHistory).where(ListenHistory.user_id == user_id)
        )
        or 0
    )

    rows = list(
        (
            await db.scalars(
                select(ListenHistory)
                .where(ListenHistory.user_id == user_id)
                .options(selectinload(ListenHistory.track))
                .order_by(ListenHistory.listened_at.desc())
                .offset(offset)
                .limit(per_page)
            )
        ).all()
    )

    return rows, total


async def record_listen(
    db: AsyncSession,
    user_id: uuid.UUID,
    track_id: uuid.UUID,
) -> ListenHistory:
    """Record a new listen event for a user.

    Args:
        db: Async database session.
        user_id: The UUID of the user.
        track_id: The UUID of the track that was listened to.

    Returns:
        The newly created ListenHistory ORM object.

    Raises:
        HTTPException: 404 if the track does not exist.
    """
    track_exists = await db.scalar(select(Track.id).where(Track.id == track_id))
    if track_exists is None:
        raise HTTPException(status_code=404, detail="Track not found")

    entry = ListenHistory(user_id=user_id, track_id=track_id)
    db.add(entry)
    await db.flush()
    await db.refresh(entry)

    # Eagerly load the track relationship so callers can serialise it
    await db.refresh(entry, attribute_names=["track"])
    return entry


async def get_likes(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Like], int]:
    """Return a paginated list of tracks liked by a user.

    Args:
        db: Async database session.
        user_id: The UUID of the user.
        page: 1-based page number.
        per_page: Number of entries per page.

    Returns:
        Tuple of (like list, total count).
    """
    offset = (page - 1) * per_page

    total: int = (
        await db.scalar(select(func.count()).select_from(Like).where(Like.user_id == user_id)) or 0
    )

    rows = list(
        (
            await db.scalars(
                select(Like)
                .where(Like.user_id == user_id)
                .options(selectinload(Like.track))
                .order_by(Like.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
        ).all()
    )

    return rows, total


async def like_track(
    db: AsyncSession,
    user_id: uuid.UUID,
    track_id: uuid.UUID,
) -> Like:
    """Like a track.  Idempotent — returns existing Like if already liked.

    Args:
        db: Async database session.
        user_id: The UUID of the user.
        track_id: The UUID of the track to like.

    Returns:
        The Like ORM object (new or existing).

    Raises:
        HTTPException: 404 if the track does not exist.
    """
    track_exists = await db.scalar(select(Track.id).where(Track.id == track_id))
    if track_exists is None:
        raise HTTPException(status_code=404, detail="Track not found")

    existing = await db.scalar(
        select(Like).where(Like.user_id == user_id, Like.track_id == track_id)
    )
    if existing is not None:
        # Ensure the track relationship is loaded before returning
        await db.refresh(existing, attribute_names=["track"])
        return existing

    like = Like(user_id=user_id, track_id=track_id)
    db.add(like)
    await db.flush()
    await db.refresh(like)
    await db.refresh(like, attribute_names=["track"])
    return like


async def unlike_track(
    db: AsyncSession,
    user_id: uuid.UUID,
    track_id: uuid.UUID,
) -> bool:
    """Remove a like.

    Args:
        db: Async database session.
        user_id: The UUID of the user.
        track_id: The UUID of the track to unlike.

    Returns:
        True if the like was found and removed, False if it did not exist.
    """
    existing = await db.scalar(
        select(Like).where(Like.user_id == user_id, Like.track_id == track_id)
    )
    if existing is None:
        return False

    await db.delete(existing)
    await db.flush()
    return True
