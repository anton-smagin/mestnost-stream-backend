"""
Seed script for Label Stream database.

Inserts 3 artists, 2 albums each, 5 tracks per album, and 1 test user.
Idempotent: check-before-insert pattern.

Usage:
    cd /workspace/backend && uv run python scripts/seed_db.py
"""

import sys
from datetime import date
from pathlib import Path

# Ensure the backend package is importable when running from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Album, Artist, Track, User


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


ARTISTS = [
    {
        "name": "The Midnight",
        "slug": "the-midnight",
        "bio": "Synthwave duo from Los Angeles blending cinematic nostalgic sound.",
        "image_url": None,
    },
    {
        "name": "Kolinga",
        "slug": "kolinga",
        "bio": "Afrobeat and jazz-funk band from Paris.",
        "image_url": None,
    },
    {
        "name": "Bonobo",
        "slug": "bonobo",
        "bio": (
            "British musician, DJ, and producer of downtempo and jazz-influenced electronic music."
        ),
        "image_url": None,
    },
]

ALBUMS: dict[str, list[dict]] = {
    "the-midnight": [
        {
            "title": "Endless Summer",
            "slug": "endless-summer",
            "cover_image_url": None,
            "release_date": date(2016, 6, 10),
        },
        {
            "title": "Monsters",
            "slug": "monsters",
            "cover_image_url": None,
            "release_date": date(2022, 1, 14),
        },
    ],
    "kolinga": [
        {
            "title": "Tola",
            "slug": "tola",
            "cover_image_url": None,
            "release_date": date(2019, 3, 22),
        },
        {
            "title": "Kota",
            "slug": "kota",
            "cover_image_url": None,
            "release_date": date(2021, 9, 17),
        },
    ],
    "bonobo": [
        {
            "title": "Black Sands",
            "slug": "black-sands",
            "cover_image_url": None,
            "release_date": date(2010, 3, 29),
        },
        {
            "title": "The North Borders",
            "slug": "the-north-borders",
            "cover_image_url": None,
            "release_date": date(2013, 4, 1),
        },
    ],
}

# 5 tracks per album keyed by album slug
TRACKS: dict[str, list[dict]] = {
    # The Midnight — Endless Summer
    "endless-summer": [
        {
            "title": "Endless Summer",
            "slug": "endless-summer",
            "track_number": 1,
            "duration_seconds": 276,
        },  # noqa: E501
        {"title": "Sunset", "slug": "sunset", "track_number": 2, "duration_seconds": 255},
        {"title": "Jason", "slug": "jason", "track_number": 3, "duration_seconds": 238},
        {
            "title": "Comeback Kid",
            "slug": "comeback-kid",
            "track_number": 4,
            "duration_seconds": 262,
        },  # noqa: E501
        {
            "title": "Crystallized",
            "slug": "crystallized",
            "track_number": 5,
            "duration_seconds": 247,
        },  # noqa: E501
    ],
    # The Midnight — Monsters
    "monsters": [
        {"title": "Monsters", "slug": "monsters", "track_number": 1, "duration_seconds": 243},
        {"title": "Deep Blue", "slug": "deep-blue", "track_number": 2, "duration_seconds": 218},
        {"title": "Avalanche", "slug": "avalanche", "track_number": 3, "duration_seconds": 234},
        {
            "title": "Better With You",
            "slug": "better-with-you",
            "track_number": 4,
            "duration_seconds": 261,
        },  # noqa: E501
        {"title": "Fire", "slug": "fire", "track_number": 5, "duration_seconds": 225},
    ],
    # Kolinga — Tola
    "tola": [
        {"title": "Tola", "slug": "tola", "track_number": 1, "duration_seconds": 304},
        {"title": "Nairobi", "slug": "nairobi", "track_number": 2, "duration_seconds": 289},
        {"title": "Banga", "slug": "banga", "track_number": 3, "duration_seconds": 312},
        {"title": "Mama Africa", "slug": "mama-africa", "track_number": 4, "duration_seconds": 278},
        {"title": "Likembe", "slug": "likembe", "track_number": 5, "duration_seconds": 295},
    ],
    # Kolinga — Kota
    "kota": [
        {"title": "Kota", "slug": "kota", "track_number": 1, "duration_seconds": 320},
        {"title": "Brazza", "slug": "brazza", "track_number": 2, "duration_seconds": 298},
        {"title": "Savane", "slug": "savane", "track_number": 3, "duration_seconds": 275},
        {
            "title": "Rhythm of the Night",
            "slug": "rhythm-of-the-night",
            "track_number": 4,
            "duration_seconds": 308,
        },
        {"title": "Harmonie", "slug": "harmonie", "track_number": 5, "duration_seconds": 285},
    ],
    # Bonobo — Black Sands
    "black-sands": [
        {"title": "Kong", "slug": "kong", "track_number": 1, "duration_seconds": 252},
        {"title": "Kiara", "slug": "kiara", "track_number": 2, "duration_seconds": 327},
        {"title": "Black Sands", "slug": "black-sands", "track_number": 3, "duration_seconds": 340},  # noqa: E501
        {
            "title": "Kiara (Reprise)",
            "slug": "kiara-reprise",
            "track_number": 4,
            "duration_seconds": 188,
        },  # noqa: E501
        {"title": "Ketto", "slug": "ketto", "track_number": 5, "duration_seconds": 295},
    ],
    # Bonobo — The North Borders
    "the-north-borders": [
        {"title": "First Fires", "slug": "first-fires", "track_number": 1, "duration_seconds": 311},  # noqa: E501
        {
            "title": "Heaven for the Sinner",
            "slug": "heaven-for-the-sinner",
            "track_number": 2,
            "duration_seconds": 298,
        },
        {"title": "Cirrus", "slug": "cirrus", "track_number": 3, "duration_seconds": 368},
        {"title": "No Reason", "slug": "no-reason", "track_number": 4, "duration_seconds": 287},
        {"title": "Ten Tigers", "slug": "ten-tigers", "track_number": 5, "duration_seconds": 322},
    ],
}

TEST_USER = {
    "email": "test@labelstream.dev",
    "display_name": "Test User",
    "password": "password123",
}


def seed(session: Session) -> None:
    """Insert seed data idempotently using check-before-insert."""
    # --- Artists ---
    artist_map: dict[str, Artist] = {}
    for artist_data in ARTISTS:
        existing = session.execute(
            select(Artist).where(Artist.slug == artist_data["slug"])
        ).scalar_one_or_none()
        if existing is None:
            artist = Artist(**artist_data)
            session.add(artist)
            session.flush()
            print(f"  Inserted artist: {artist_data['name']}")
            artist_map[artist_data["slug"]] = artist
        else:
            print(f"  Artist already exists: {artist_data['name']}")
            artist_map[artist_data["slug"]] = existing

    # --- Albums ---
    album_map: dict[str, Album] = {}
    for artist_slug, albums in ALBUMS.items():
        artist = artist_map[artist_slug]
        for album_data in albums:
            existing = session.execute(
                select(Album).where(
                    Album.artist_id == artist.id,
                    Album.slug == album_data["slug"],
                )
            ).scalar_one_or_none()
            if existing is None:
                album = Album(**album_data, artist_id=artist.id)
                session.add(album)
                session.flush()
                print(f"  Inserted album: {album_data['title']}")
                album_map[album_data["slug"]] = album
            else:
                print(f"  Album already exists: {album_data['title']}")
                album_map[album_data["slug"]] = existing

    # --- Tracks ---
    for album_slug, tracks in TRACKS.items():
        album = album_map[album_slug]
        for track_data in tracks:
            existing = session.execute(
                select(Track).where(
                    Track.album_id == album.id,
                    Track.slug == track_data["slug"],
                )
            ).scalar_one_or_none()
            if existing is None:
                track = Track(**track_data, album_id=album.id)
                session.add(track)
                print(f"  Inserted track: {track_data['title']} ({album_slug})")
            else:
                print(f"  Track already exists: {track_data['title']} ({album_slug})")

    # --- Test User ---
    existing_user = session.execute(
        select(User).where(User.email == TEST_USER["email"])
    ).scalar_one_or_none()
    if existing_user is None:
        user = User(
            email=TEST_USER["email"],
            display_name=TEST_USER["display_name"],
            password_hash=hash_password(TEST_USER["password"]),
        )
        session.add(user)
        print(f"  Inserted user: {TEST_USER['email']}")
    else:
        print(f"  User already exists: {TEST_USER['email']}")

    session.commit()
    print("\nSeed complete.")


def main() -> None:
    engine = create_engine(settings.database_url_sync, echo=False)
    print("Seeding database...")
    with Session(engine) as session:
        seed(session)
    engine.dispose()


if __name__ == "__main__":
    main()
