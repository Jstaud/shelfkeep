from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.metadata import lookup_isbn, looks_like_isbn, normalize_isbn, search_title
from app.models import Book, Collection, HouseholdItem, Room
from app.routers.pages import default_collection
from app.schemas import BookCreate, BookOut, ItemOut, RoomCreate, RoomOut
from app.serializers import book_out, item_out, room_out
from app.uploads import save_bytes, save_upload

router = APIRouter(prefix="/api")


@router.get("/lookup")
async def lookup(q: str = "", isbn: str = "") -> dict:
    query = (isbn or q).strip()
    if not query:
        raise HTTPException(status_code=400, detail="Provide an ISBN or title to look up")

    if looks_like_isbn(query):
        match = await lookup_isbn(query)
        return {
            "query": query,
            "kind": "isbn",
            "results": [match.model_dump() if match else None],
            "found": bool(match),
        }

    results = await search_title(query)
    return {
        "query": query,
        "kind": "title",
        "results": [r.model_dump() for r in results],
        "found": bool(results),
    }


@router.get("/books", response_model=list[BookOut])
def list_books(db: Session = Depends(get_db)):
    books = db.scalars(select(Book).order_by(Book.created_at.desc())).all()
    return [book_out(b) for b in books]


@router.post("/books", response_model=BookOut, status_code=201)
async def create_book(payload: BookCreate, db: Session = Depends(get_db)):
    collection = None
    if payload.collection_id:
        collection = db.get(Collection, payload.collection_id)
    if not collection:
        collection = default_collection(db)

    isbn = normalize_isbn(payload.isbn) if payload.isbn else None
    cover_path = None
    cover_url = payload.cover_url
    if cover_url and cover_url.startswith("https://covers.openlibrary.org/"):
        cover_path = await _cache_cover(cover_url)

    book = Book(
        collection_id=collection.id,
        title=payload.title.strip(),
        subtitle=payload.subtitle,
        authors=payload.authors,
        isbn=isbn,
        publisher=payload.publisher,
        published_year=payload.published_year,
        page_count=payload.page_count,
        description=payload.description,
        cover_path=cover_path,
        cover_url=cover_url,
        openlibrary_url=payload.openlibrary_url,
        notes=payload.notes,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book_out(book)


@router.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book_out(book)


@router.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
    return None


@router.get("/rooms", response_model=list[RoomOut])
def list_rooms(db: Session = Depends(get_db)):
    rooms = db.scalars(
        select(Room).options(selectinload(Room.items)).order_by(Room.sort_order, Room.name)
    ).all()
    return [room_out(r) for r in rooms]


@router.post("/rooms", response_model=RoomOut, status_code=201)
def create_room(payload: RoomCreate, db: Session = Depends(get_db)):
    room = Room(name=payload.name.strip(), description=payload.description)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room_out(room)


@router.get("/rooms/{room_id}", response_model=RoomOut)
def get_room(room_id: int, db: Session = Depends(get_db)):
    room = db.scalar(select(Room).options(selectinload(Room.items)).where(Room.id == room_id))
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room_out(room)


@router.delete("/rooms/{room_id}", status_code=204)
def delete_room(room_id: int, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    db.delete(room)
    db.commit()
    return None


@router.post("/items", response_model=ItemOut, status_code=201)
async def create_item(
    room_id: int = Form(...),
    name: str = Form(...),
    brand: str | None = Form(default=None),
    model: str | None = Form(default=None),
    serial_number: str | None = Form(default=None),
    purchase_date: str | None = Form(default=None),
    replacement_value: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    photo: UploadFile | None = File(default=None),
    receipt: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    room = db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not name.strip():
        raise HTTPException(status_code=400, detail="Name is required")

    parsed_date = _parse_date(purchase_date)
    parsed_value = _parse_money(replacement_value)
    photo_path = None
    receipt_path = None
    if photo and photo.filename:
        photo_path = await save_upload(photo, "photos")
    if receipt and receipt.filename:
        receipt_path = await save_upload(receipt, "receipts", receipt=True)

    item = HouseholdItem(
        room_id=room.id,
        name=name.strip(),
        brand=_blank(brand),
        model=_blank(model),
        serial_number=_blank(serial_number),
        purchase_date=parsed_date,
        replacement_value=parsed_value,
        photo_path=photo_path,
        receipt_path=receipt_path,
        notes=_blank(notes),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    item.room = room
    return item_out(item)


@router.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.scalar(
        select(HouseholdItem).options(selectinload(HouseholdItem.room)).where(
            HouseholdItem.id == item_id
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item_out(item)


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(HouseholdItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return None


def _blank(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Purchase date must be YYYY-MM-DD") from exc


def _parse_money(value: str | None) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        amount = Decimal(str(value).replace(",", "").replace("$", "").strip())
    except InvalidOperation as exc:
        raise HTTPException(status_code=400, detail="Replacement value must be a number") from exc
    if amount < 0:
        raise HTTPException(status_code=400, detail="Replacement value cannot be negative")
    return amount.quantize(Decimal("0.01"))


async def _cache_cover(url: str) -> str | None:
    import httpx

    from app.metadata import USER_AGENT

    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
        if response.status_code != 200:
            return None
        content_type = response.headers.get("content-type", "")
        if "image" not in content_type or len(response.content) < 800:
            return None
        suffix = ".jpg"
        if "png" in content_type:
            suffix = ".png"
        elif "webp" in content_type:
            suffix = ".webp"
        return save_bytes(response.content, "covers", suffix)
    except httpx.HTTPError:
        return None

