import datetime
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.core.database import async_session
from app.main import app
from app.models.album import Album
from app.models.artist import Artist
from app.models.track import Track
from app.models.user import User
from app.services.auth import create_access_token, hash_password


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def db_session():
    """Provide an AsyncSession for direct DB manipulation in tests.

    Rolls back after each test to keep the DB clean.
    """
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def sample_user():
    """Create a test user committed to the DB so HTTP requests can see it.

    Uses its own session and commits so that API test requests (which open
    separate DB connections) can see the data.  Performs a hard-delete cleanup
    after the test.
    """
    user_id = uuid.uuid4()
    async with async_session() as session:
        user = User(
            id=user_id,
            email=f"fixture_user_{user_id.hex[:8]}@test.example",
            display_name="Fixture User",
            password_hash=hash_password("test-password-123"),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    yield user

    async with async_session() as session:
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


@pytest.fixture
async def auth_token(sample_user) -> str:
    """Return a valid JWT token string for *sample_user*."""
    return create_access_token(str(sample_user.id))


@pytest.fixture
async def auth_headers(auth_token) -> dict[str, str]:
    """Return Authorization header dict for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
async def sample_artist():
    """Create a test artist with one album and two tracks, committed to the DB.

    Uses its own session and commits so that API test requests (which open
    separate DB connections) can see the data.  Performs a hard-delete cleanup
    after the test instead of relying on rollback.
    """
    artist_id = uuid.uuid4()
    album_id = uuid.uuid4()
    track1_id = uuid.uuid4()
    track2_id = uuid.uuid4()

    async with async_session() as session:
        artist = Artist(
            id=artist_id,
            name="Test Artist",
            slug=f"test-artist-{artist_id.hex[:8]}",
            bio="A test artist bio.",
            image_url="https://example.com/artist.jpg",
        )
        session.add(artist)
        await session.flush()

        album = Album(
            id=album_id,
            title="Test Album",
            slug=f"test-album-{album_id.hex[:8]}",
            artist_id=artist.id,
            cover_image_url="https://example.com/cover.jpg",
            release_date=datetime.date(2024, 1, 15),
        )
        session.add(album)
        await session.flush()

        track1 = Track(
            id=track1_id,
            title="First Track",
            slug=f"first-track-{track1_id.hex[:8]}",
            album_id=album.id,
            track_number=1,
            duration_seconds=210,
            file_key="tracks/test-artist/test-album/1_first-track.flac",
        )
        track2 = Track(
            id=track2_id,
            title="Second Track",
            slug=f"second-track-{track2_id.hex[:8]}",
            album_id=album.id,
            track_number=2,
            duration_seconds=195,
            file_key="tracks/test-artist/test-album/2_second-track.flac",
        )
        session.add(track1)
        session.add(track2)
        await session.commit()
        await session.refresh(artist)
        await session.refresh(album)
        await session.refresh(track1)
        await session.refresh(track2)

    # Attach album/track references for convenient test access
    artist._test_album = album
    artist._test_track1 = track1
    artist._test_track2 = track2

    yield artist

    # Cleanup: use core DELETE so the DB-level CASCADE removes albums/tracks
    # without the ORM trying to NULL-out the FK first.
    async with async_session() as session:
        await session.execute(delete(Artist).where(Artist.id == artist_id))
        await session.commit()
