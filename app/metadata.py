"""Open Library lookup. Public APIs, no Amazon or proprietary sources."""

from __future__ import annotations

import re
from typing import Any

import httpx

from app.schemas import BookLookup

USER_AGENT = "Shelfkeep/0.1 (https://github.com/Jstaud/shelfkeep; self-hosted catalog)"
BOOKS_URL = "https://openlibrary.org/api/books"
SEARCH_URL = "https://openlibrary.org/search.json"
ISBN_URL = "https://openlibrary.org/isbn/{isbn}.json"
COVER_ISBN = "https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
COVER_ID = "https://covers.openlibrary.org/b/id/{cover_id}-L.jpg?default=false"

ISBN_RE = re.compile(r"[^0-9Xx]")


def normalize_isbn(raw: str) -> str:
    return ISBN_RE.sub("", (raw or "").strip())


def looks_like_isbn(raw: str) -> bool:
    value = normalize_isbn(raw)
    return len(value) in {10, 13} and value[:-1].isdigit()


def _year_from(value: Any) -> str | None:
    if not value:
        return None
    text = str(value)
    match = re.search(r"(1[0-9]{3}|20[0-9]{2})", text)
    return match.group(1) if match else text[:20]


def _authors_from_data(payload: dict[str, Any]) -> str | None:
    authors = payload.get("authors") or []
    names = [a.get("name") for a in authors if isinstance(a, dict) and a.get("name")]
    if not names and isinstance(payload.get("author_name"), list):
        names = [str(n) for n in payload["author_name"] if n]
    return ", ".join(names) if names else None


def _publishers_from_data(payload: dict[str, Any]) -> str | None:
    pubs = payload.get("publishers") or []
    if pubs and isinstance(pubs[0], dict):
        names = [p.get("name") for p in pubs if p.get("name")]
        return ", ".join(names) if names else None
    if pubs and isinstance(pubs[0], str):
        return ", ".join(str(p) for p in pubs)
    name = payload.get("publisher")
    return str(name) if name else None


def _cover_from_data(payload: dict[str, Any], isbn: str | None) -> str | None:
    cover = payload.get("cover") or {}
    if isinstance(cover, dict):
        for key in ("large", "medium", "small"):
            if cover.get(key):
                return str(cover[key])
    cover_i = payload.get("cover_i")
    if cover_i:
        return COVER_ID.format(cover_id=cover_i)
    if isbn:
        return COVER_ISBN.format(isbn=isbn)
    return None


def _excerpt(payload: dict[str, Any]) -> str | None:
    excerpts = payload.get("excerpts") or []
    if excerpts and isinstance(excerpts[0], dict):
        text = excerpts[0].get("text")
        return str(text) if text else None
    desc = payload.get("description")
    if isinstance(desc, dict):
        return desc.get("value")
    if isinstance(desc, str):
        return desc
    return None


def book_from_ol_data(payload: dict[str, Any], isbn: str | None = None) -> BookLookup:
    identifiers = payload.get("identifiers") or {}
    isbn_val = isbn
    if not isbn_val:
        for key in ("isbn_13", "isbn_10"):
            values = identifiers.get(key) or []
            if values:
                isbn_val = normalize_isbn(str(values[0]))
                break
    if not isbn_val and payload.get("isbn"):
        first = payload["isbn"]
        isbn_val = normalize_isbn(str(first[0] if isinstance(first, list) else first))

    return BookLookup(
        title=payload.get("title") or payload.get("title_suggest"),
        subtitle=payload.get("subtitle"),
        authors=_authors_from_data(payload),
        isbn=isbn_val,
        publisher=_publishers_from_data(payload),
        published_year=_year_from(
            payload.get("publish_date") or payload.get("first_publish_year")
        ),
        page_count=payload.get("number_of_pages") or payload.get("number_of_pages_median"),
        description=_excerpt(payload),
        cover_url=_cover_from_data(payload, isbn_val),
        openlibrary_url=payload.get("url") or payload.get("key") and (
            f"https://openlibrary.org{payload['key']}"
            if str(payload["key"]).startswith("/")
            else str(payload["key"])
        ),
        source="openlibrary",
    )


async def lookup_isbn(isbn: str, client: httpx.AsyncClient | None = None) -> BookLookup | None:
    isbn = normalize_isbn(isbn)
    if not looks_like_isbn(isbn):
        return None

    own_client = client is None
    client = client or httpx.AsyncClient(
        timeout=8.0,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )
    try:
        response = await client.get(
            BOOKS_URL,
            params={"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"},
        )
        if response.status_code == 200:
            data = response.json()
            payload = data.get(f"ISBN:{isbn}")
            if payload:
                return book_from_ol_data(payload, isbn)

        # Fallback: edition JSON by ISBN (also a documented Open Library route).
        response = await client.get(ISBN_URL.format(isbn=isbn))
        if response.status_code == 200:
            payload = response.json()
            if payload.get("title"):
                cover_ids = payload.get("covers") or []
                if cover_ids and not payload.get("cover"):
                    payload["cover"] = {"large": COVER_ID.format(cover_id=cover_ids[0])}
                return book_from_ol_data(payload, isbn)
    except httpx.HTTPError:
        return None
    finally:
        if own_client:
            await client.aclose()
    return None


async def search_title(query: str, client: httpx.AsyncClient | None = None) -> list[BookLookup]:
    q = (query or "").strip()
    if len(q) < 2:
        return []

    own_client = client is None
    client = client or httpx.AsyncClient(
        timeout=8.0,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )
    try:
        response = await client.get(
            SEARCH_URL,
            params={"title": q, "limit": 6, "fields": "key,title,subtitle,author_name,first_publish_year,isbn,cover_i,publisher,number_of_pages_median"},
        )
        if response.status_code != 200:
            return []
        docs = response.json().get("docs") or []
        results: list[BookLookup] = []
        for doc in docs:
            book = book_from_ol_data(doc)
            if book.title:
                results.append(book)
        return results
    except httpx.HTTPError:
        return []
    finally:
        if own_client:
            await client.aclose()
