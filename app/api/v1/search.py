"""Search routes — GET /api/v1/search/?q={query}.

Mounted at /api/v1/search in app.main.
"""

from fastapi import APIRouter, Query

from app.core.deps import DB
from app.core.response import ok
from app.schemas.album import AlbumSummary
from app.schemas.artist import ArtistSummary
from app.schemas.search import SearchResults
from app.schemas.track import TrackSummary
from app.services.search import search as search_service

router = APIRouter()


@router.get("/")
async def search_endpoint(
    db: DB,
    q: str = Query(default=""),
) -> dict:
    """Search artists, albums, and tracks by name/title.

    Returns up to 5 results per entity type.  An empty query returns empty
    result lists without an error.
    """
    results = await search_service(db=db, query=q)

    artists = [ArtistSummary.model_validate(a) for a in results["artists"]]
    albums = [AlbumSummary.model_validate(a) for a in results["albums"]]
    tracks = [TrackSummary.model_validate(t) for t in results["tracks"]]

    payload = SearchResults(
        artists=artists,
        albums=albums,
        tracks=tracks,
    ).model_dump(mode="json")

    total = len(artists) + len(albums) + len(tracks)
    return ok(payload, page=1, total=total)
