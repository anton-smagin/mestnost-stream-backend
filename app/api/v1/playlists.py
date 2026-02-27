"""Playlist routes — /api/v1/playlists/*.

All endpoints require a valid JWT token (CurrentUserID dependency).
Mounted at /api/v1/playlists in app.main.
"""

import uuid

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.core.deps import DB, CurrentUserID
from app.core.response import ok
from app.schemas.playlist import (
    AddTrackRequest,
    CreatePlaylistRequest,
    PlaylistDetail,
    PlaylistSummary,
    PlaylistTrackEntry,
    UpdatePlaylistRequest,
)
from app.services.playlist import (
    add_track_to_playlist,
    create_playlist,
    delete_playlist,
    get_playlist,
    list_playlists,
    remove_track_from_playlist,
    update_playlist,
)

router = APIRouter()


@router.get("/")
async def list_playlists_endpoint(
    db: DB,
    user_id: CurrentUserID,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> dict:
    """List playlists owned by the authenticated user."""
    playlists, total = await list_playlists(
        db=db, user_id=uuid.UUID(user_id), page=page, per_page=per_page
    )
    return ok(
        [PlaylistSummary.model_validate(p).model_dump(mode="json") for p in playlists],
        page=page,
        total=total,
    )


@router.post("/")
async def create_playlist_endpoint(
    body: CreatePlaylistRequest,
    db: DB,
    user_id: CurrentUserID,
) -> dict:
    """Create a new playlist for the authenticated user."""
    playlist = await create_playlist(
        db=db,
        user_id=uuid.UUID(user_id),
        name=body.name,
        is_public=body.is_public,
    )
    return ok(PlaylistSummary.model_validate(playlist).model_dump(mode="json"))


@router.get("/{playlist_id}")
async def get_playlist_endpoint(
    playlist_id: uuid.UUID,
    db: DB,
    user_id: CurrentUserID,
) -> dict:
    """Return playlist detail with all tracks."""
    playlist = await get_playlist(db=db, playlist_id=playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return ok(PlaylistDetail.model_validate(playlist).model_dump(mode="json"))


@router.put("/{playlist_id}")
async def update_playlist_endpoint(
    playlist_id: uuid.UUID,
    body: UpdatePlaylistRequest,
    db: DB,
    user_id: CurrentUserID,
) -> dict:
    """Update the name and/or visibility of a playlist."""
    playlist = await update_playlist(
        db=db,
        playlist_id=playlist_id,
        user_id=uuid.UUID(user_id),
        name=body.name,
        is_public=body.is_public,
    )
    return ok(PlaylistSummary.model_validate(playlist).model_dump(mode="json"))


@router.delete("/{playlist_id}", status_code=204)
async def delete_playlist_endpoint(
    playlist_id: uuid.UUID,
    db: DB,
    user_id: CurrentUserID,
) -> Response:
    """Delete a playlist.  Returns 204 on success."""
    await delete_playlist(db=db, playlist_id=playlist_id, user_id=uuid.UUID(user_id))
    return Response(status_code=204)


@router.post("/{playlist_id}/tracks")
async def add_track_endpoint(
    playlist_id: uuid.UUID,
    body: AddTrackRequest,
    db: DB,
    user_id: CurrentUserID,
) -> dict:
    """Add a track to a playlist."""
    pt = await add_track_to_playlist(
        db=db,
        playlist_id=playlist_id,
        user_id=uuid.UUID(user_id),
        track_id=body.track_id,
    )
    return ok(PlaylistTrackEntry.model_validate(pt).model_dump(mode="json"))


@router.delete("/{playlist_id}/tracks/{track_id}", status_code=204)
async def remove_track_endpoint(
    playlist_id: uuid.UUID,
    track_id: uuid.UUID,
    db: DB,
    user_id: CurrentUserID,
) -> Response:
    """Remove a track from a playlist.  Returns 204 on success."""
    await remove_track_from_playlist(
        db=db,
        playlist_id=playlist_id,
        user_id=uuid.UUID(user_id),
        track_id=track_id,
    )
    return Response(status_code=204)
