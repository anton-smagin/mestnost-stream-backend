"""CLI script to bulk-upload track audio files from a local directory to R2.

Expected directory structure:
    <dir>/
      <artist-slug>/
        <album-slug>/
          <NN>_<track-slug>.flac   (e.g. 01_endless-summer.flac)

For each file the script:
  1. Parses artist slug, album slug, track number, and track slug from the path.
  2. Looks up the corresponding Track row in the database.
  3. Uploads the audio bytes to R2 using the storage service.
  4. Updates the track's file_key in the database.

Usage:
    cd /workspace/backend
    uv run python scripts/upload_tracks.py /path/to/audio/directory

Options:
    --dry-run   Parse and validate paths without uploading or updating the DB.
"""

import argparse
import asyncio
import logging
import re
import sys
from pathlib import Path

# Make the app package importable when running from the scripts/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.album import Album
from app.models.artist import Artist
from app.models.track import Track
from app.services.storage import compute_file_key, upload_track

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Matches filenames like "01_track-slug.flac" or "1_track-slug.mp3"
FILENAME_RE = re.compile(r"^(\d+)_(.+)\.[a-zA-Z0-9]+$")


def parse_audio_path(root: Path, file_path: Path) -> tuple[str, str, int, str] | None:
    """Extract (artist_slug, album_slug, track_number, track_slug) from an audio file path.

    Args:
        root: The top-level directory passed on the CLI.
        file_path: Absolute path to the audio file.

    Returns:
        A 4-tuple on success, or None if the path does not match the expected layout.
    """
    try:
        relative = file_path.relative_to(root)
    except ValueError:
        return None

    parts = relative.parts
    if len(parts) != 3:  # artist_slug/album_slug/filename
        return None

    artist_slug, album_slug, filename = parts
    m = FILENAME_RE.match(filename)
    if m is None:
        return None

    track_number = int(m.group(1))
    track_slug = m.group(2)
    return artist_slug, album_slug, track_number, track_slug


def collect_audio_files(root: Path) -> list[Path]:
    """Walk *root* and return all files that look like audio tracks."""
    audio_extensions = {".flac", ".mp3", ".aac", ".wav", ".ogg"}
    return sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in audio_extensions
    )


async def _upload_one(
    file_path: Path,
    track: Track,
    file_key: str,
    dry_run: bool,
) -> bool:
    """Upload a single file and update the DB record.

    Args:
        file_path: Local path to the audio file.
        track: ORM Track object to update.
        file_key: Destination R2 object key.
        dry_run: If True, skip the actual upload and DB write.

    Returns:
        True on success, False on failure.
    """
    content_type_map = {
        ".flac": "audio/flac",
        ".mp3": "audio/mpeg",
        ".aac": "audio/aac",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
    }
    content_type = content_type_map.get(file_path.suffix.lower(), "application/octet-stream")

    if dry_run:
        logger.info("[DRY RUN] Would upload %s → %s", file_path, file_key)
        return True

    audio_bytes = file_path.read_bytes()
    await upload_track(file_data=audio_bytes, file_key=file_key, content_type=content_type)
    logger.info("Uploaded %s → %s", file_path.name, file_key)
    return True


def run_upload(root: Path, dry_run: bool) -> None:
    """Main upload loop: scan files, match DB records, upload, update DB.

    Args:
        root: Root directory containing artist/album/track structure.
        dry_run: Skip actual R2 and DB operations when True.
    """
    engine = create_engine(settings.database_url_sync, echo=False)

    audio_files = collect_audio_files(root)
    if not audio_files:
        logger.warning("No audio files found under %s", root)
        return

    logger.info("Found %d audio file(s) to process.", len(audio_files))

    succeeded: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    with Session(engine) as session:
        for file_path in audio_files:
            parsed = parse_audio_path(root, file_path)
            if parsed is None:
                logger.warning("Skipping (unexpected path layout): %s", file_path)
                skipped.append(str(file_path))
                continue

            artist_slug, album_slug, track_number, track_slug = parsed

            # Look up artist
            artist = session.execute(
                select(Artist).where(Artist.slug == artist_slug)
            ).scalar_one_or_none()
            if artist is None:
                logger.warning(
                    "Skipping %s — artist slug %r not found in DB",
                    file_path.name,
                    artist_slug,
                )
                skipped.append(str(file_path))
                continue

            # Look up album
            album = session.execute(
                select(Album).where(Album.artist_id == artist.id, Album.slug == album_slug)
            ).scalar_one_or_none()
            if album is None:
                logger.warning(
                    "Skipping %s — album slug %r not found for artist %r",
                    file_path.name,
                    album_slug,
                    artist_slug,
                )
                skipped.append(str(file_path))
                continue

            # Look up track
            track = session.execute(
                select(Track).where(
                    Track.album_id == album.id,
                    Track.track_number == track_number,
                )
            ).scalar_one_or_none()
            if track is None:
                logger.warning(
                    "Skipping %s — track number %d not found in album %r",
                    file_path.name,
                    track_number,
                    album_slug,
                )
                skipped.append(str(file_path))
                continue

            file_key = compute_file_key(
                artist_slug=artist_slug,
                album_slug=album_slug,
                track_number=track_number,
                track_slug=track_slug,
            )

            try:
                ok = asyncio.run(
                    _upload_one(
                        file_path=file_path,
                        track=track,
                        file_key=file_key,
                        dry_run=dry_run,
                    )
                )
            except Exception:
                logger.exception("Upload failed for %s", file_path.name)
                failed.append(str(file_path))
                continue

            if ok:
                if not dry_run:
                    track.file_key = file_key
                    session.add(track)
                succeeded.append(str(file_path))

        if not dry_run and succeeded:
            session.commit()
            logger.info("DB updated for %d track(s).", len(succeeded))

    engine.dispose()

    print("\n--- Summary ---")
    print(f"  Succeeded : {len(succeeded)}")
    print(f"  Skipped   : {len(skipped)}")
    print(f"  Failed    : {len(failed)}")

    if failed:
        print("\nFailed files:")
        for f in failed:
            print(f"  {f}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload local audio files to R2 and update the Label Stream database."
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Root directory containing artist/album/track audio files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse paths and validate DB records without uploading or writing.",
    )
    args = parser.parse_args()

    root: Path = args.directory.resolve()
    if not root.is_dir():
        logger.error("Directory not found: %s", root)
        sys.exit(1)

    run_upload(root=root, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
