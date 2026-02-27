"""User / Me routes — /api/v1/me/*.

All endpoints require a valid JWT token (CurrentUserID dependency).
Mounted at /api/v1/me in app.main.
"""

import uuid

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.core.deps import DB, CurrentUserID
from app.core.response import ok
from app.schemas.user import LikeEntry, ListenHistoryEntry, RecordListenRequest, UserProfile
from app.services.user import (
    get_likes,
    get_listen_history,
    get_user_profile,
    like_track,
    record_listen,
    unlike_track,
)

router = APIRouter()


@router.get("/")
async def get_profile(db: DB, user_id: CurrentUserID) -> dict:
    """Return the authenticated user's profile."""
    user = await get_user_profile(db=db, user_id=uuid.UUID(user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return ok(UserProfile.model_validate(user).model_dump(mode="json"))


@router.get("/history")
async def get_history(
    db: DB,
    user_id: CurrentUserID,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Return a paginated listen history for the authenticated user."""
    history, total = await get_listen_history(
        db=db,
        user_id=uuid.UUID(user_id),
        page=page,
        per_page=per_page,
    )
    return ok(
        [ListenHistoryEntry.model_validate(h).model_dump(mode="json") for h in history],
        page=page,
        total=total,
    )


@router.post("/history")
async def post_history(
    body: RecordListenRequest,
    db: DB,
    user_id: CurrentUserID,
) -> dict:
    """Record a listen event for the authenticated user."""
    entry = await record_listen(
        db=db,
        user_id=uuid.UUID(user_id),
        track_id=body.track_id,
    )
    return ok(ListenHistoryEntry.model_validate(entry).model_dump(mode="json"))


@router.get("/likes")
async def get_likes_endpoint(
    db: DB,
    user_id: CurrentUserID,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Return a paginated list of tracks liked by the authenticated user."""
    likes, total = await get_likes(
        db=db,
        user_id=uuid.UUID(user_id),
        page=page,
        per_page=per_page,
    )
    return ok(
        [LikeEntry.model_validate(like).model_dump(mode="json") for like in likes],
        page=page,
        total=total,
    )


@router.post("/likes/{track_id}")
async def like_track_endpoint(
    track_id: uuid.UUID,
    db: DB,
    user_id: CurrentUserID,
) -> dict:
    """Like a track.  Idempotent — always returns 200."""
    like = await like_track(
        db=db,
        user_id=uuid.UUID(user_id),
        track_id=track_id,
    )
    return ok(LikeEntry.model_validate(like).model_dump(mode="json"))


@router.delete("/likes/{track_id}", status_code=204)
async def unlike_track_endpoint(
    track_id: uuid.UUID,
    db: DB,
    user_id: CurrentUserID,
) -> Response:
    """Unlike a track.  Returns 204 on success, 404 if the like did not exist."""
    removed = await unlike_track(
        db=db,
        user_id=uuid.UUID(user_id),
        track_id=track_id,
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Like not found")
    return Response(status_code=204)
