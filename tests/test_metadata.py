from app.metadata import book_from_ol_data, looks_like_isbn, normalize_isbn


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
