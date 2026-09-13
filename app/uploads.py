from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

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
READ_CHUNK_BYTES = 64 * 1024
# One item request may include a photo, a receipt, and small form fields.
MAX_UPLOAD_BODY_BYTES = MAX_IMAGE_BYTES + MAX_RECEIPT_BYTES + READ_CHUNK_BYTES


class _RequestBodyTooLarge(BaseException):
    """Bypass Starlette ExceptionMiddleware so the ASGI cap can respond 400."""


def _too_large_response() -> JSONResponse:
    return JSONResponse({"detail": "File is too large"}, status_code=status.HTTP_400_BAD_REQUEST)


class MaxBodySizeMiddleware:
    """Reject oversized bodies before FastAPI/Starlette spool multipart parts."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        max_size = MAX_UPLOAD_BODY_BYTES
        content_length = Headers(scope=scope).get("content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                declared = 0
            if declared > max_size:
                await _too_large_response()(scope, receive, send)
                return

        received = 0

        async def limited_receive() -> dict:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > max_size:
                    raise _RequestBodyTooLarge()
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _RequestBodyTooLarge:
            await _too_large_response()(scope, receive, send)


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
    limit = MAX_RECEIPT_BYTES if receipt else MAX_IMAGE_BYTES
    data = await read_upload_limited(file, limit)
    if suffix != ".pdf":
        _assert_image(data)
    name = f"{uuid.uuid4().hex}{suffix}"
    relative = f"{folder}/{name}"
    dest = safe_join(relative)
    dest.write_bytes(data)
    return relative


async def read_upload_limited(file: UploadFile, limit: int) -> bytes:
    """Read an upload in bounded chunks and abort as soon as it exceeds limit."""
    chunks: list[bytes] = []
    total = 0
    while True:
        remaining = limit - total
        chunk = await file.read(READ_CHUNK_BYTES if remaining >= READ_CHUNK_BYTES else remaining + 1)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is too large")
        chunks.append(chunk)
    return b"".join(chunks)


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
