import asyncio
import json
from unittest.mock import AsyncMock

from app.metadata import book_from_ol_data, lookup_isbn, looks_like_isbn, normalize_isbn, search_title
from app.schemas import BookCreate


def test_normalize_isbn_strips_hyphens():
    assert normalize_isbn("978-0-547-92822-7") == "9780547928227"


def test_looks_like_isbn():
    assert looks_like_isbn("9780547928227")
    assert looks_like_isbn("0-547-92822-X")
    assert not looks_like_isbn("The Hobbit")
    assert not looks_like_isbn("123")


def test_book_from_open_library_payload():
    payload = {
        "title": "The Hobbit",
        "subtitle": "There and Back Again",
        "authors": [{"name": "J.R.R. Tolkien"}],
        "publishers": [{"name": "Houghton Mifflin"}],
        "publish_date": "2012",
        "number_of_pages": 300,
        "url": "https://openlibrary.org/books/OL123M",
        "cover": {"large": "https://covers.openlibrary.org/b/id/1-L.jpg"},
        "identifiers": {"isbn_13": ["9780547928227"]},
    }
    book = book_from_ol_data(payload)
    assert book.title == "The Hobbit"
    assert book.authors == "J.R.R. Tolkien"
    assert book.isbn == "9780547928227"
    assert book.cover_url.endswith("1-L.jpg")
    assert book.source == "openlibrary"


def test_authors_are_truncated_to_create_schema_limit():
    names = [{"name": f"Author {i:03d} " + ("X" * 40)} for i in range(20)]
    book = book_from_ol_data({"title": "Anthology", "authors": names})
    assert book.authors is not None
    assert len(book.authors) <= 500
    BookCreate(title="Anthology", authors=book.authors)


def test_publisher_list_is_joined():
    book = book_from_ol_data(
        {
            "title": "Collected Essays",
            "publisher": ["Harper", "Collins"],
        }
    )
    assert book.publisher == "Harper, Collins"
    assert "[" not in book.publisher


def test_malformed_lookup_json_is_failure_not_error():
    class BrokenResponse:
        status_code = 200

        def json(self):
            raise json.JSONDecodeError("Expecting value", "", 0)

    client = AsyncMock()
    client.get = AsyncMock(return_value=BrokenResponse())

    assert asyncio.run(lookup_isbn("9780547928227", client=client)) is None
    assert asyncio.run(search_title("The Hobbit", client=client)) == []


def test_malformed_search_docs_is_lookup_miss():
    class DocsResponse:
        status_code = 200

        def json(self):
            return {"docs": 1}

    client = AsyncMock()
    client.get = AsyncMock(return_value=DocsResponse())

    assert asyncio.run(search_title("The Hobbit", client=client)) == []


def test_malformed_fallback_covers_does_not_raise():
    class BooksMiss:
        status_code = 200

        def json(self):
            return {}

    class BadCovers:
        status_code = 200

        def json(self):
            return {"title": "The Hobbit", "covers": 1}

    client = AsyncMock()
    client.get = AsyncMock(side_effect=[BooksMiss(), BadCovers()])

    result = asyncio.run(lookup_isbn("9780547928227", client=client))
    assert result is not None
    assert result.title == "The Hobbit"
