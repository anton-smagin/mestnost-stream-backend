"""R2-compatible S3 storage service for audio files."""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def compute_file_key(artist_slug: str, album_slug: str, track_number: int, track_slug: str) -> str:
    """Compute R2 object key from path components.

    Args:
        artist_slug: URL-safe artist slug.
        album_slug: URL-safe album slug.
        track_number: 1-based track number (zero-padded to two digits).
        track_slug: URL-safe track slug.

    Returns:
        R2 object key in the form tracks/{artist_slug}/{album_slug}/{NN}_{track_slug}.flac
    """
    return f"tracks/{artist_slug}/{album_slug}/{track_number:02d}_{track_slug}.flac"


async def get_presigned_url(file_key: str) -> str:
    """Generate a presigned GET URL for the given file_key (1-hour expiry).

    In mock mode (r2_endpoint is empty), returns a placeholder URL so that
    development and tests work without real R2 credentials.

    Args:
        file_key: R2 object key (e.g. tracks/artist/album/01_title.flac).

    Returns:
        A presigned HTTPS URL that grants temporary read access to the object.
    """
    if not settings.r2_endpoint:
        return f"https://mock-r2.dev/{file_key}?expires=3600"

    import aioboto3  # noqa: PLC0415

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key,
        aws_secret_access_key=settings.r2_secret_key,
        region_name="auto",
    ) as client:
        url: str = await client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.r2_bucket, "Key": file_key},
            ExpiresIn=settings.presigned_url_expiry,
        )
        return url


async def upload_track(file_data: bytes, file_key: str, content_type: str = "audio/flac") -> str:
    """Upload audio file bytes to R2 and return the file_key.

    In mock mode, logs the intent and returns the key without making any
    network calls.

    Args:
        file_data: Raw audio bytes.
        file_key: Destination R2 object key.
        content_type: MIME type for the object (default audio/flac).

    Returns:
        The file_key that was uploaded.
    """
    if not settings.r2_endpoint:
        logger.info("Mock mode: would upload %s (%d bytes)", file_key, len(file_data))
        return file_key

    import aioboto3  # noqa: PLC0415

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key,
        aws_secret_access_key=settings.r2_secret_key,
        region_name="auto",
    ) as client:
        await client.put_object(
            Bucket=settings.r2_bucket,
            Key=file_key,
            Body=file_data,
            ContentType=content_type,
        )
        return file_key


async def delete_track(file_key: str) -> None:
    """Delete an audio file from R2.

    In mock mode, logs the intent without making any network calls.

    Args:
        file_key: R2 object key to delete.
    """
    if not settings.r2_endpoint:
        logger.info("Mock mode: would delete %s", file_key)
        return

    import aioboto3  # noqa: PLC0415

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key,
        aws_secret_access_key=settings.r2_secret_key,
        region_name="auto",
    ) as client:
        await client.delete_object(Bucket=settings.r2_bucket, Key=file_key)
