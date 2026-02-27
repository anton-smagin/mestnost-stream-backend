"""Artist routes — GET /api/v1/artists and GET /api/v1/artists/{slug}.

Mounted at /api/v1/artists in app.main.
"""

from fastapi import APIRouter, HTTPException, Query

from app.core.deps import DB
from app.core.response import ok
from app.schemas.artist import ArtistDetail, ArtistSummary
from app.services.artist import get_artist_by_slug, list_artists

router = APIRouter()


@router.get("/")
async def list_artists_endpoint(
    db: DB,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Return a paginated list of artists."""
    artists, total = await list_artists(db=db, page=page, per_page=per_page)
    return ok(
        [ArtistSummary.model_validate(a).model_dump(mode="json") for a in artists],
        page=page,
        total=total,
    )


@router.get("/{slug}")
async def get_artist_endpoint(slug: str, db: DB) -> dict:
    """Return artist detail including albums list, or 404 if not found."""
    artist = await get_artist_by_slug(db=db, slug=slug)
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found")
    return ok(ArtistDetail.model_validate(artist).model_dump(mode="json"))
