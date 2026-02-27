"""Admin service — create artists, albums, and upload tracks."""

import logging
import re
import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.album import Album
from app.models.artist import Artist
from app.models.track import Track
from app.services import storage

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """Convert a display title to a URL-safe slug.

    Lowercases the text and replaces spaces with hyphens.  Non-alphanumeric
    characters (other than hyphens) are removed.

    Args:
        text: Human-readable title string.

    Returns:
        A lowercase, hyphen-separated slug string.
    """
    slug = text.lower().strip()
    # Replace spaces (and runs of whitespace) with hyphens
    slug = re.sub(r"\s+", "-", slug)
    # Remove any character that is not alphanumeric or a hyphen
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    # Collapse multiple consecutive hyphens
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-")


async def create_artist(
    db: AsyncSession,
    name: str,
    slug: str,
    bio: str | None = None,
    image_url: str | None = None,
) -> Artist:
    """Create a new Artist record and persist it.

    Args:
        db: Async database session.
        name: Display name of the artist.
        slug: Unique URL-safe identifier.
        bio: Optional long-form biography text.
        image_url: Optional URL to the artist's portrait image.

    Returns:
        The newly created Artist ORM object.

    Raises:
        HTTPException: 409 if an artist with the same slug already exists.
    """
    existing = await db.scalar(select(Artist).where(Artist.slug == slug))
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Artist slug '{slug}' is already taken")

    artist = Artist(
        id=uuid.uuid4(),
        name=name,
        slug=slug,
        bio=bio,
        image_url=image_url,
    )
    db.add(artist)
    await db.flush()
    await db.refresh(artist)
    return artist


async def create_album(
    db: AsyncSession,
    title: str,
    slug: str,
    artist_id: uuid.UUID,
    cover_image_url: str | None,
    release_date: date,
) -> Album:
    """Create a new Album record and persist it.

    Args:
        db: Async database session.
        title: Display title of the album.
        slug: URL-safe identifier (unique within the artist).
        artist_id: UUID of the owning artist.
        cover_image_url: Optional URL to the album artwork.
        release_date: Official release date of the album.

    Returns:
        The newly created Album ORM object (artist relationship loaded).

    Raises:
        HTTPException: 404 if the artist does not exist.
        HTTPException: 409 if the artist already has an album with this slug.
    """
    artist = await db.scalar(select(Artist).where(Artist.id == artist_id))
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found")

    existing = await db.scalar(
        select(Album).where(Album.artist_id == artist_id, Album.slug == slug)
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Album slug '{slug}' is already taken for this artist",
        )

    album = Album(
        id=uuid.uuid4(),
        title=title,
        slug=slug,
        artist_id=artist_id,
        cover_image_url=cover_image_url,
        release_date=release_date,
    )
    db.add(album)
    await db.flush()
    await db.refresh(album)
    return album


async def upload_track(
    db: AsyncSession,
    title: str,
    album_id: uuid.UUID,
    track_number: int,
    duration_seconds: int,
    audio_file_data: bytes,
    audio_content_type: str,
) -> Track:
    """Upload an audio file to R2 and create the corresponding Track record.

    Looks up the album and its artist to compute the canonical R2 file key,
    uploads the audio bytes, then inserts a Track row with the resulting key.

    Args:
        db: Async database session.
        title: Display title of the track.
        album_id: UUID of the owning album.
        track_number: 1-based position in the album.
        duration_seconds: Track length in whole seconds.
        audio_file_data: Raw audio bytes (e.g. FLAC content).
        audio_content_type: MIME type of the uploaded file.

    Returns:
        The newly created Track ORM object.

    Raises:
        HTTPException: 404 if the album or its artist does not exist.
        HTTPException: 409 if a track with the same slug already exists on this album.
        HTTPException: 503 if the R2 upload fails.
    """
    album = await db.scalar(
        select(Album).where(Album.id == album_id).options(selectinload(Album.artist))
    )
    if album is None:
        raise HTTPException(status_code=404, detail="Album not found")

    # artist is eagerly loaded via selectinload above
    artist: Artist = album.artist  # type: ignore[assignment]

    track_slug = _slugify(title)

    existing = await db.scalar(
        select(Track).where(Track.album_id == album_id, Track.slug == track_slug)
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Track slug '{track_slug}' is already taken on this album",
        )

    file_key = storage.compute_file_key(
        artist_slug=artist.slug,
        album_slug=album.slug,
        track_number=track_number,
        track_slug=track_slug,
    )

    try:
        await storage.upload_track(
            file_data=audio_file_data,
            file_key=file_key,
            content_type=audio_content_type,
        )
    except Exception as exc:
        logger.exception("R2 upload failed for track %r (album %s)", title, album_id)
        raise HTTPException(
            status_code=503,
            detail="Audio upload temporarily unavailable. Please try again later.",
        ) from exc

    track = Track(
        id=uuid.uuid4(),
        title=title,
        slug=track_slug,
        album_id=album_id,
        track_number=track_number,
        duration_seconds=duration_seconds,
        file_key=file_key,
    )
    db.add(track)
    await db.flush()
    await db.refresh(track)
    return track
