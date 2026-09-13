import asyncio

import pytest
from fastapi import HTTPException
from starlette.formparsers import MultiPartParser
from starlette.responses import JSONResponse

from app.uploads import (
    MAX_UPLOAD_BODY_BYTES,
    READ_CHUNK_BYTES,
    MaxBodySizeMiddleware,
    read_upload_limited,
    save_upload,
)


class FakeUpload:
    def __init__(self, payload: bytes, content_type: str = "image/png", filename: str = "x.png"):
        self.filename = filename
        self.content_type = content_type
        self._data = payload
        self._pos = 0
        self.bytes_consumed = 0

    async def read(self, size: int = -1) -> bytes:
        if size < 0:
            chunk = self._data[self._pos :]
        else:
            chunk = self._data[self._pos : self._pos + size]
        self._pos += len(chunk)
        self.bytes_consumed = self._pos
        return chunk


def test_read_upload_limited_stops_after_limit():
    payload = b"x" * (READ_CHUNK_BYTES * 3)
    upload = FakeUpload(payload)
    with pytest.raises(HTTPException) as err:
        asyncio.run(read_upload_limited(upload, 100))
    assert err.value.status_code == 400
    assert "too large" in err.value.detail.lower()
    assert upload.bytes_consumed <= 101


def test_read_upload_limited_returns_small_file():
    upload = FakeUpload(b"hello")
    assert asyncio.run(read_upload_limited(upload, 100)) == b"hello"


def test_save_upload_rejects_oversize_before_image_parse(tmp_path, monkeypatch):
    from app import uploads as uploads_mod

    monkeypatch.setattr(uploads_mod, "MAX_IMAGE_BYTES", 80)
    monkeypatch.setattr(uploads_mod.settings, "data_dir", tmp_path)
    uploads_mod.ensure_dirs()
    upload = FakeUpload(b"y" * 200)
    with pytest.raises(HTTPException) as err:
        asyncio.run(save_upload(upload, "photos"))
    assert err.value.status_code == 400
    assert "too large" in err.value.detail.lower()
    assert upload.bytes_consumed <= 81
    assert not list((tmp_path / "uploads" / "photos").glob("*"))


def test_oversize_content_length_rejected_before_multipart_parse(auth_client, monkeypatch):
    from app import uploads as uploads_mod

    monkeypatch.setattr(uploads_mod, "MAX_UPLOAD_BODY_BYTES", 800)
    parsed = {"called": False}
    original = MultiPartParser.parse

    async def wrapped(self, *args, **kwargs):
        parsed["called"] = True
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(MultiPartParser, "parse", wrapped)

    room = auth_client.post("/api/rooms", json={"name": "Limit Lab"})
    room_id = room.json()["id"]
    response = auth_client.post(
        "/api/items",
        data={"room_id": str(room_id), "name": "Huge"},
        files={"photo": ("huge.png", b"x" * 4000, "image/png")},
    )
    assert response.status_code == 400
    assert "too large" in response.json()["detail"].lower()
    assert parsed["called"] is False


def test_max_body_middleware_rejects_declared_length_without_calling_app(monkeypatch):
    from app import uploads as uploads_mod

    monkeypatch.setattr(uploads_mod, "MAX_UPLOAD_BODY_BYTES", 50)
    called = {"inner": False}

    async def inner(scope, receive, send):
        called["inner"] = True
        await JSONResponse({"ok": True})(scope, receive, send)

    middleware = MaxBodySizeMiddleware(inner)

    async def receive():
        return {"type": "http.request", "body": b"x" * 200, "more_body": False}

    sent: list[dict] = []

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/items",
        "raw_path": b"/api/items",
        "query_string": b"",
        "headers": [(b"content-length", b"200")],
        "client": ("test", 123),
        "server": ("test", 80),
    }
    asyncio.run(middleware(scope, receive, send))
    assert called["inner"] is False
    start = next(message for message in sent if message["type"] == "http.response.start")
    assert start["status"] == 400


def test_max_body_middleware_stops_streaming_after_limit(monkeypatch):
    from app import uploads as uploads_mod

    monkeypatch.setattr(uploads_mod, "MAX_UPLOAD_BODY_BYTES", 100)
    passed_to_app = {"bytes": 0}

    async def inner(scope, receive, send):
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            passed_to_app["bytes"] += len(message.get("body", b""))
            if not message.get("more_body"):
                break
        await JSONResponse({"ok": True})(scope, receive, send)

    middleware = MaxBodySizeMiddleware(inner)
    chunks = [b"a" * 40, b"b" * 40, b"c" * 40]
    index = {"i": 0}

    async def receive():
        i = index["i"]
        if i >= len(chunks):
            return {"type": "http.disconnect"}
        chunk = chunks[i]
        index["i"] += 1
        return {"type": "http.request", "body": chunk, "more_body": i < len(chunks) - 1}

    sent: list[dict] = []

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/items",
        "raw_path": b"/api/items",
        "query_string": b"",
        "headers": [(b"content-type", b"multipart/form-data; boundary=----x")],
        "client": ("test", 123),
        "server": ("test", 80),
    }
    asyncio.run(middleware(scope, receive, send))
    assert passed_to_app["bytes"] <= 100
    start = next(message for message in sent if message["type"] == "http.response.start")
    assert start["status"] == 400


def test_documented_upload_body_cap_covers_photo_and_receipt():
    from app.uploads import MAX_IMAGE_BYTES, MAX_RECEIPT_BYTES

    assert MAX_UPLOAD_BODY_BYTES >= MAX_IMAGE_BYTES + MAX_RECEIPT_BYTES
    assert MAX_IMAGE_BYTES == 10 * 1024 * 1024
    assert MAX_RECEIPT_BYTES == 15 * 1024 * 1024
