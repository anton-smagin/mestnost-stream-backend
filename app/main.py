from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Router registration — uncomment as you build each resource
# from app.api.v1 import artists, albums, tracks, search, users, playlists, admin
# app.include_router(artists.router, prefix="/api/v1/artists", tags=["artists"])
# app.include_router(albums.router, prefix="/api/v1/albums", tags=["albums"])
# app.include_router(tracks.router, prefix="/api/v1/tracks", tags=["tracks"])
# app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
# app.include_router(users.router, prefix="/api/v1/me", tags=["users"])
# app.include_router(playlists.router, prefix="/api/v1/playlists", tags=["playlists"])
# app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
