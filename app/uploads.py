from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.config import settings

IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
RECEIPT_TYPES = {
    **IMAGE_TYPES,
    "application/pdf": ".pdf",
}

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_RECEIPT_BYTES = 15 * 1024 * 1024


def ensure_dirs() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    for folder in ("covers", "photos", "receipts"):
        (settings.uploads_dir / folder).mkdir(parents=True, exist_ok=True)


def media_url(relative: str | None) -> str | None:
    if not relative:
        return None
    return f"/media/{relative}"


def safe_join(relative: str) -> Path:
    root = settings.uploads_dir.resolve()
    target = (settings.uploads_dir / relative).resolve()
    if not str(target).startswith(str(root)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    return target


async def save_upload(file: UploadFile, folder: str, *, receipt: bool = False) -> str:
    allowed = RECEIPT_TYPES if receipt else IMAGE_TYPES
    content_type = (file.content_type or "").lower()
    suffix = allowed.get(content_type)
    if not suffix:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Use JPEG, PNG, WebP"
            + (" or PDF" if receipt else "")
            + ".",
        )
    data = await file.read()
    limit = MAX_RECEIPT_BYTES if receipt else MAX_IMAGE_BYTES
    if len(data) > limit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is too large")
    if suffix != ".pdf":
        _assert_image(data)
    name = f"{uuid.uuid4().hex}{suffix}"
    relative = f"{folder}/{name}"
    dest = safe_join(relative)
    dest.write_bytes(data)
    return relative


def delete_stored_file(relative: str | None) -> None:
    if not relative:
        return
    try:
        path = safe_join(relative)
    except HTTPException:
        return
    if path.is_file():
        path.unlink()


def save_bytes(data: bytes, folder: str, suffix: str = ".jpg") -> str:
    name = f"{uuid.uuid4().hex}{suffix}"
    relative = f"{folder}/{name}"
    dest = safe_join(relative)
    dest.write_bytes(data)
    return relative


def _assert_image(data: bytes) -> None:
    try:
        from io import BytesIO

        with Image.open(BytesIO(data)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File is not a valid image"
        ) from exc
