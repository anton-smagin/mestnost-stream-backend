"""Playlist service — CRUD and track management for user playlists."""

import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.playlist import Playlist, PlaylistTrack
from app.models.track import Track


async def list_playlists(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Playlist], int]:
    """Return playlists owned by a user, paginated.

    Args:
        db: Async database session.
        user_id: The UUID of the owning user.
        page: Page number (1-indexed).
        per_page: Number of results per page.

    Returns:
        Tuple of (list of Playlist ORM objects, total count).
    """
    total = (
        await db.scalar(
            select(func.count()).select_from(Playlist).where(Playlist.user_id == user_id)
        )
    ) or 0
    offset = (page - 1) * per_page
    rows = list(
        (
            await db.scalars(
                select(Playlist)
                .where(Playlist.user_id == user_id)
                .order_by(Playlist.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
        ).all()
    )
    return rows, total


async def create_playlist(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    is_public: bool = False,
) -> Playlist:
    """Create a new playlist for a user.

    Args:
        db: Async database session.
        user_id: The UUID of the owning user.
        name: Display name for the playlist.
        is_public: Whether the playlist is publicly visible.

    Returns:
        The newly created Playlist ORM object.
    """
    playlist = Playlist(user_id=user_id, name=name, is_public=is_public)
    db.add(playlist)
    await db.flush()
    await db.refresh(playlist)
    return playlist


async def get_playlist(
    db: AsyncSession,
    playlist_id: uuid.UUID,
) -> Playlist | None:
    """Return a playlist by ID with its tracks eagerly loaded, ordered by position.

    Args:
        db: Async database session.
        playlist_id: The UUID primary key of the playlist.

    Returns:
        The Playlist ORM object with playlist_tracks and their tracks loaded,
        or None if not found.
    """
    playlist = await db.scalar(
        select(Playlist)
        .where(Playlist.id == playlist_id)
        .options(selectinload(Playlist.playlist_tracks).selectinload(PlaylistTrack.track))
    )
    if playlist is not None:
        playlist.playlist_tracks.sort(key=lambda pt: pt.position)
    return playlist


async def update_playlist(
    db: AsyncSession,
    playlist_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str | None,
    is_public: bool | None,
) -> Playlist:
    """Update playlist name and/or visibility.

    Args:
        db: Async database session.
        playlist_id: The UUID of the playlist to update.
        user_id: The UUID of the requesting user (ownership check).
        name: New name, or None to leave unchanged.
        is_public: New visibility flag, or None to leave unchanged.

    Returns:
        The updated Playlist ORM object.

    Raises:
        HTTPException: 404 if the playlist does not exist.
        HTTPException: 403 if the user does not own the playlist.
    """
    playlist = await db.scalar(select(Playlist).where(Playlist.id == playlist_id))
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if playlist.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if name is not None:
        playlist.name = name
    if is_public is not None:
        playlist.is_public = is_public

    await db.flush()
    await db.refresh(playlist)
    return playlist


async def delete_playlist(
    db: AsyncSession,
    playlist_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Delete a playlist.

    Args:
        db: Async database session.
        playlist_id: The UUID of the playlist to delete.
        user_id: The UUID of the requesting user (ownership check).

    Returns:
        True if the playlist was deleted.

    Raises:
        HTTPException: 404 if the playlist does not exist.
        HTTPException: 403 if the user does not own the playlist.
    """
    playlist = await db.scalar(select(Playlist).where(Playlist.id == playlist_id))
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if playlist.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await db.delete(playlist)
    await db.flush()
    return True


async def add_track_to_playlist(
    db: AsyncSession,
    playlist_id: uuid.UUID,
    user_id: uuid.UUID,
    track_id: uuid.UUID,
) -> PlaylistTrack:
    """Append a track to a playlist at the next available position.

    Args:
        db: Async database session.
        playlist_id: The UUID of the playlist.
        user_id: The UUID of the requesting user (ownership check).
        track_id: The UUID of the track to add.

    Returns:
        The newly created PlaylistTrack ORM object with track loaded.

    Raises:
        HTTPException: 404 if the playlist or track does not exist.
        HTTPException: 403 if the user does not own the playlist.
    """
    playlist = await db.scalar(select(Playlist).where(Playlist.id == playlist_id))
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if playlist.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    track_exists = await db.scalar(select(Track.id).where(Track.id == track_id))
    if track_exists is None:
        raise HTTPException(status_code=404, detail="Track not found")

    # Determine next position (max + 1, or 1 if playlist is empty)
    max_position: int = (
        await db.scalar(
            select(func.max(PlaylistTrack.position)).where(PlaylistTrack.playlist_id == playlist_id)
        )
    ) or 0

    pt = PlaylistTrack(
        playlist_id=playlist_id,
        track_id=track_id,
        position=max_position + 1,
    )
    db.add(pt)
    await db.flush()
    await db.refresh(pt)
    await db.refresh(pt, attribute_names=["track"])
    return pt


async def remove_track_from_playlist(
    db: AsyncSession,
    playlist_id: uuid.UUID,
    user_id: uuid.UUID,
    track_id: uuid.UUID,
) -> bool:
    """Remove a track from a playlist and compact remaining positions.

    Args:
        db: Async database session.
        playlist_id: The UUID of the playlist.
        user_id: The UUID of the requesting user (ownership check).
        track_id: The UUID of the track to remove.

    Returns:
        True if the track was removed.

    Raises:
        HTTPException: 404 if the playlist does not exist or the track is not in it.
        HTTPException: 403 if the user does not own the playlist.
    """
    playlist = await db.scalar(select(Playlist).where(Playlist.id == playlist_id))
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if playlist.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    pt = await db.scalar(
        select(PlaylistTrack).where(
            PlaylistTrack.playlist_id == playlist_id,
            PlaylistTrack.track_id == track_id,
        )
    )
    if pt is None:
        raise HTTPException(status_code=404, detail="Track not in playlist")

    removed_position = pt.position
    await db.delete(pt)
    await db.flush()

    # Compact positions: decrement all entries that came after the removed one
    remaining = list(
        (
            await db.scalars(
                select(PlaylistTrack)
                .where(
                    PlaylistTrack.playlist_id == playlist_id,
                    PlaylistTrack.position > removed_position,
                )
                .order_by(PlaylistTrack.position)
            )
        ).all()
    )
    for entry in remaining:
        entry.position -= 1

    await db.flush()
    return True
