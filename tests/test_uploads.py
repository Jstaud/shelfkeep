import asyncio

import pytest
from fastapi import HTTPException

from app.uploads import READ_CHUNK_BYTES, read_upload_limited, save_upload


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
