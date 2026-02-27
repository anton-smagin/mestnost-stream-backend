from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import albums, artists, auth, playlists, search, tracks, users
from app.core.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Convert HTTPException into the standard API envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"data": None, "error": exc.detail, "meta": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert validation errors into the standard API envelope."""
    return JSONResponse(
        status_code=422,
        content={"data": None, "error": str(exc.errors()), "meta": None},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(artists.router, prefix="/api/v1/artists", tags=["artists"])
app.include_router(albums.router, prefix="/api/v1/albums", tags=["albums"])
app.include_router(tracks.router, prefix="/api/v1/tracks", tags=["tracks"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(users.router, prefix="/api/v1/me", tags=["users"])
app.include_router(playlists.router, prefix="/api/v1/playlists", tags=["playlists"])

# Router registration — uncomment as you build each resource
# from app.api.v1 import admin
# app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
