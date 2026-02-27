"""Artist service — list and retrieve artist records."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.artist import Artist


async def list_artists(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Artist], int]:
    """Return a paginated list of artists and the total count.

    Args:
        db: Async database session.
        page: 1-based page number.
        per_page: Number of results per page.

    Returns:
        Tuple of (artist list, total count).
    """
    offset = (page - 1) * per_page

    total: int = await db.scalar(select(func.count()).select_from(Artist)) or 0

    result = await db.scalars(select(Artist).order_by(Artist.name).offset(offset).limit(per_page))
    artists = list(result.all())

    return artists, total


async def get_artist_by_slug(db: AsyncSession, slug: str) -> Artist | None:
    """Return an Artist by slug with albums eagerly loaded, or None if not found.

    Args:
        db: Async database session.
        slug: The unique artist slug.

    Returns:
        The Artist ORM object with albums loaded, or None.
    """
    return await db.scalar(
        select(Artist).where(Artist.slug == slug).options(selectinload(Artist.albums))
    )
