"""Album routes — GET /api/v1/albums/{id}.

Mounted at /api/v1/albums in app.main.
"""

import uuid

from fastapi import APIRouter, HTTPException

from app.core.deps import DB
from app.core.response import ok
from app.schemas.album import AlbumDetail
from app.services.album import get_album

router = APIRouter()


@router.get("/{album_id}")
async def get_album_endpoint(album_id: uuid.UUID, db: DB) -> dict:
    """Return album detail with tracks ordered by track_number, or 404 if not found."""
    album = await get_album(db=db, album_id=album_id)
    if album is None:
        raise HTTPException(status_code=404, detail="Album not found")
    return ok(AlbumDetail.model_validate(album).model_dump(mode="json"))
