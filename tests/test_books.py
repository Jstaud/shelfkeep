from unittest.mock import AsyncMock, patch

from app.schemas import BookLookup


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
