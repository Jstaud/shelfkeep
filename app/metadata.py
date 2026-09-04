"""Open Library lookup. Public APIs, no Amazon or proprietary sources."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from pydantic import ValidationError

from app import __version__
from app.schemas import BookLookup

USER_AGENT = (
    f"Shelfkeep/{__version__} "
    "(https://github.com/Jstaud/shelfkeep; self-hosted catalog)"
)
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
    if not names:
        return None
    return ", ".join(names)[:500]


def _publisher_names(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, dict):
        name = value.get("name")
        return [str(name)] if name else []
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            names.extend(_publisher_names(item))
        return names
    text = str(value).strip()
    return [text] if text else []


def _publishers_from_data(payload: dict[str, Any]) -> str | None:
    names = _publisher_names(payload.get("publishers")) or _publisher_names(
        payload.get("publisher")
    )
    if not names:
        return None
    joined = ", ".join(names)
    return joined[:300]


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


def _json_object(response: httpx.Response) -> dict[str, Any] | None:
    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _safe_book(payload: Any, isbn: str | None = None) -> BookLookup | None:
    if not isinstance(payload, dict):
        return None
    try:
        return book_from_ol_data(payload, isbn)
    except (TypeError, ValueError, AttributeError, KeyError, ValidationError):
        return None


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
            data = _json_object(response)
            payload = data.get(f"ISBN:{isbn}") if data else None
            book = _safe_book(payload, isbn)
            if book:
                return book

        # Fallback: edition JSON by ISBN (also a documented Open Library route).
        response = await client.get(ISBN_URL.format(isbn=isbn))
        if response.status_code == 200:
            payload = _json_object(response)
            if payload and payload.get("title"):
                covers = payload.get("covers")
                if (
                    isinstance(covers, list)
                    and covers
                    and not payload.get("cover")
                ):
                    payload["cover"] = {"large": COVER_ID.format(cover_id=covers[0])}
                book = _safe_book(payload, isbn)
                if book:
                    return book
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
        body = _json_object(response)
        if not body:
            return []
        docs = body.get("docs")
        if not isinstance(docs, list):
            return []
        results: list[BookLookup] = []
        for doc in docs:
            book = _safe_book(doc)
            if book and book.title:
                results.append(book)
        return results
    except httpx.HTTPError:
        return []
    finally:
        if own_client:
            await client.aclose()
