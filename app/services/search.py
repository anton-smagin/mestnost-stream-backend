"""Search service — full-text similarity search across artists, albums, and tracks."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.album import Album
from app.models.artist import Artist
from app.models.track import Track

# Maximum number of results returned per entity type
_RESULTS_PER_TYPE = 5


async def search(
    db: AsyncSession,
    query: str,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """Search artists, albums, and tracks by name/title using ILIKE.

    Uses case-insensitive ILIKE pattern matching as a fallback that works
    reliably whether or not pg_trgm is installed.  Results are limited to
    _RESULTS_PER_TYPE entries per entity type.

    Args:
        db: Async database session.
        query: The search string supplied by the client.
        page: Unused — kept for interface consistency.
        per_page: Unused — kept for interface consistency.

    Returns:
        Dict with keys ``artists``, ``albums``, and ``tracks``, each a list of
        ORM objects.
    """
    if not query or not query.strip():
        return {"artists": [], "albums": [], "tracks": []}

    pattern = f"%{query.strip()}%"

    artists = list(
        (
            await db.scalars(
                select(Artist)
                .where(or_(Artist.name.ilike(pattern), Artist.slug.ilike(pattern)))
                .limit(_RESULTS_PER_TYPE)
            )
        ).all()
    )

    albums = list(
        (
            await db.scalars(
                select(Album)
                .where(or_(Album.title.ilike(pattern), Album.slug.ilike(pattern)))
                .limit(_RESULTS_PER_TYPE)
            )
        ).all()
    )

    tracks = list(
        (
            await db.scalars(
                select(Track)
                .where(or_(Track.title.ilike(pattern), Track.slug.ilike(pattern)))
                .limit(_RESULTS_PER_TYPE)
            )
        ).all()
    )

    return {"artists": artists, "albums": albums, "tracks": tracks}
