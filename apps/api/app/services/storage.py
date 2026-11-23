"""Local image storage for listing photos.

The first version stores files on the API host and serves them from
``/media``. The public interface only exposes a relative URL, so an
S3/MinIO implementation can replace :func:`save_listing_image` without
touching the routers or the web client.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


class ImageValidationError(ValueError):
    """Raised when an uploaded file is not an accepted image."""


@dataclass(frozen=True)
class StoredImage:
    image_url: str
    content_type: str
    byte_size: int


# Magic-byte signatures are authoritative; the browser-provided content type
# is never trusted on its own.
_SIGNATURES: tuple[tuple[str, str, bytes], ...] = (
    ("image/jpeg", ".jpg", b"\xff\xd8\xff"),
    ("image/png", ".png", b"\x89PNG\r\n\x1a\n"),
    ("image/webp", ".webp", b"RIFF"),
)


def _detect_content_type(data: bytes) -> tuple[str, str] | None:
    for content_type, extension, signature in _SIGNATURES:
        if data.startswith(signature):
            if content_type == "image/webp" and data[8:12] != b"WEBP":
                continue
            return content_type, extension
    return None


def save_listing_image(data: bytes, declared_content_type: str | None) -> StoredImage:
    if not data:
        raise ImageValidationError("The uploaded file is empty")
    if len(data) > settings.max_image_bytes:
        raise ImageValidationError(
            f"The image exceeds the {settings.max_image_bytes // (1024 * 1024)} MB limit"
        )

    detected = _detect_content_type(data)
    if detected is None:
        raise ImageValidationError("Only JPEG, PNG and WebP images are accepted")

    content_type, extension = detected
    if declared_content_type and declared_content_type not in {
        content_type,
        "image/jpg",
        "application/octet-stream",
    }:
        raise ImageValidationError("The declared content type does not match the image data")

    directory = Path(settings.upload_dir) / "listings"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{extension}"
    (directory / filename).write_bytes(data)

    return StoredImage(
        image_url=f"{settings.media_url_prefix.rstrip('/')}/listings/{filename}",
        content_type=content_type,
        byte_size=len(data),
    )
