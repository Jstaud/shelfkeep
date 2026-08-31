from unittest.mock import AsyncMock, patch

from sqlalchemy.orm import Session

from app.config import settings
from app.schemas import BookLookup
from app.uploads import save_bytes


def test_manual_book_lands_on_shelf(auth_client):
    response = auth_client.post(
        "/api/books",
        json={"title": "Handmade Atlas", "authors": "A. Cartographer", "isbn": "0000000000"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Handmade Atlas"
    assert body["cover_src"] is None

    library = auth_client.get("/")
    assert library.status_code == 200
    assert "Handmade Atlas" in library.text

    listed = auth_client.get("/api/books")
    assert any(book["title"] == "Handmade Atlas" for book in listed.json())


def test_isbn_lookup_uses_open_library_and_falls_back(auth_client):
    match = BookLookup(
        title="The Hobbit",
        authors="J.R.R. Tolkien",
        isbn="9780547928227",
        cover_url="https://covers.openlibrary.org/b/isbn/9780547928227-L.jpg",
        openlibrary_url="https://openlibrary.org/books/OL1M",
    )
    with patch("app.routers.api.lookup_isbn", new=AsyncMock(return_value=match)):
        found = auth_client.get("/api/lookup", params={"q": "9780547928227"})
    assert found.status_code == 200
    assert found.json()["found"] is True
    assert found.json()["results"][0]["title"] == "The Hobbit"

    with patch("app.routers.api.lookup_isbn", new=AsyncMock(return_value=None)):
        missing = auth_client.get("/api/lookup", params={"q": "9780000000002"})
    assert missing.status_code == 200
    assert missing.json()["found"] is False

    created = auth_client.post(
        "/api/books",
        json={"title": "Unknown Field Guide", "isbn": "9780000000002"},
    )
    assert created.status_code == 201
    assert created.json()["title"] == "Unknown Field Guide"


def test_delete_book_removes_cached_cover(auth_client):
    relative = save_bytes(b"x" * 1200, "covers", ".jpg")
    stored = settings.uploads_dir / relative

    async def fake_cache(_url: str) -> str:
        return relative

    with patch("app.routers.api._cache_cover", new=fake_cache):
        created = auth_client.post(
            "/api/books",
            json={
                "title": "Covered Atlas",
                "cover_url": "https://covers.openlibrary.org/b/isbn/9780000000000-L.jpg",
            },
        )
    assert created.status_code == 201
    cover_src = created.json()["cover_src"]
    assert stored.is_file()
    assert auth_client.get(cover_src).status_code == 200
    assert auth_client.delete(f"/api/books/{created.json()['id']}").status_code == 204
    assert auth_client.get(cover_src).status_code == 404
    assert not stored.exists()


def test_failed_book_commit_removes_cached_cover(auth_client, monkeypatch):
    relative = save_bytes(b"x" * 1200, "covers", ".jpg")
    stored = settings.uploads_dir / relative

    async def fake_cache(_url: str) -> str:
        return relative

    def fail_commit(self):
        raise RuntimeError("commit failed")

    monkeypatch.setattr(Session, "commit", fail_commit)
    with patch("app.routers.api._cache_cover", new=fake_cache):
        try:
            auth_client.post(
                "/api/books",
                json={
                    "title": "Lost Cover",
                    "cover_url": "https://covers.openlibrary.org/b/isbn/9780000000000-L.jpg",
                },
            )
        except RuntimeError:
            pass
    assert not stored.exists()
