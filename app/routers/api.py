from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.metadata import lookup_isbn, looks_like_isbn, normalize_isbn, search_title
from app.models import Book, Borrower, Collection, HouseholdItem, Loan, Room
from app.routers.pages import default_collection
from app.schemas import (
    MEDIA_TYPES,
    BookCreate,
    BookOut,
    BorrowerCreate,
    BorrowerOut,
    BorrowerUpdate,
    ItemOut,
    LoanCreate,
    LoanOut,
    LoanReturn,
    RoomCreate,
    RoomOut,
)
from app.serializers import (
    active_loans_map,
    book_out,
    borrower_out,
    item_out,
    loan_out,
    loan_titles,
    room_out,
)
from app.uploads import delete_stored_file, save_bytes, save_upload

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
def list_books(media_type: str | None = None, db: Session = Depends(get_db)):
    if media_type:
        normalized = media_type.strip().lower()
        if normalized not in MEDIA_TYPES:
            raise HTTPException(status_code=400, detail="media_type must be book, movie, disc, or game")
        media_type = normalized
    query = select(Book).order_by(Book.created_at.desc())
    if media_type:
        query = query.where(Book.media_type == media_type)
    books = db.scalars(query).all()
    loans = active_loans_map(db)
    return [book_out(book, loans.get(("book", book.id))) for book in books]


@router.post("/books", response_model=BookOut, status_code=201)
async def create_book(payload: BookCreate, db: Session = Depends(get_db)):
    collection = None
    if payload.collection_id:
        collection = db.get(Collection, payload.collection_id)
    if not collection:
        collection = default_collection(db)

    isbn = normalize_isbn(payload.isbn) if payload.isbn else None
    page_count = _bound_page_count(payload.page_count)
    cover_path = None
    cover_url = payload.cover_url
    persisted = False
    try:
        if cover_url and cover_url.startswith("https://covers.openlibrary.org/"):
            cover_path = await _cache_cover(cover_url)
        book = Book(
            collection_id=collection.id,
            media_type=payload.media_type,
            title=payload.title,
            subtitle=payload.subtitle,
            authors=payload.authors,
            isbn=isbn,
            publisher=payload.publisher,
            published_year=payload.published_year,
            page_count=page_count,
            description=payload.description,
            cover_path=cover_path,
            cover_url=cover_url,
            openlibrary_url=payload.openlibrary_url,
            notes=payload.notes,
        )
        db.add(book)
        db.commit()
        persisted = True
        db.refresh(book)
    except Exception:
        if not persisted:
            db.rollback()
            delete_stored_file(cover_path)
        raise
    return book_out(book)


@router.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book_out(book, _active_loan(db, "book", book.id))


@router.put("/books/{book_id}", response_model=BookOut)
async def update_book(book_id: int, payload: BookCreate, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    isbn = normalize_isbn(payload.isbn) if payload.isbn else None
    page_count = _bound_page_count(payload.page_count)
    book.media_type = payload.media_type
    book.title = payload.title
    book.subtitle = payload.subtitle
    book.authors = payload.authors
    book.isbn = isbn
    book.publisher = payload.publisher
    book.published_year = payload.published_year
    book.page_count = page_count
    book.description = payload.description
    book.notes = payload.notes
    if payload.cover_url:
        book.cover_url = payload.cover_url
    if payload.openlibrary_url:
        book.openlibrary_url = payload.openlibrary_url
    db.commit()
    db.refresh(book)
    return book_out(book, _active_loan(db, "book", book.id))


@router.post("/books/{book_id}/cover", response_model=BookOut)
async def upload_book_cover(
    book_id: int,
    cover: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if not cover.filename:
        raise HTTPException(status_code=400, detail="Cover file is required")
    previous = book.cover_path
    cover_path = None
    persisted = False
    try:
        cover_path = await save_upload(cover, "covers")
        book.cover_path = cover_path
        db.commit()
        persisted = True
        db.refresh(book)
    except Exception:
        if not persisted:
            db.rollback()
            delete_stored_file(cover_path)
        raise
    delete_stored_file(previous)
    return book_out(book, _active_loan(db, "book", book.id))


@router.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    cover_path = book.cover_path
    _delete_loans_for(db, "book", book.id)
    db.delete(book)
    db.commit()
    delete_stored_file(cover_path)
    return None


@router.get("/rooms", response_model=list[RoomOut])
def list_rooms(db: Session = Depends(get_db)):
    rooms = db.scalars(
        select(Room).options(selectinload(Room.items)).order_by(Room.sort_order, Room.name)
    ).all()
    return [room_out(r) for r in rooms]


@router.post("/rooms", response_model=RoomOut, status_code=201)
def create_room(payload: RoomCreate, db: Session = Depends(get_db)):
    room = Room(name=payload.name, description=payload.description)
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
    room = db.scalar(select(Room).options(selectinload(Room.items)).where(Room.id == room_id))
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    paths = [item.photo_path for item in room.items] + [item.receipt_path for item in room.items]
    for item in room.items:
        _delete_loans_for(db, "item", item.id)
    db.delete(room)
    db.commit()
    for path in paths:
        delete_stored_file(path)
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

    item_name = _limited(name, field="Name", max_length=300, required=True)
    item_brand = _limited(brand, field="Brand", max_length=200)
    item_model = _limited(model, field="Model", max_length=200)
    item_serial = _limited(serial_number, field="Serial number", max_length=200)
    parsed_date = _parse_date(purchase_date)
    parsed_value = _parse_money(replacement_value)

    photo_path = None
    receipt_path = None
    persisted = False
    try:
        if photo and photo.filename:
            photo_path = await save_upload(photo, "photos")
        if receipt and receipt.filename:
            receipt_path = await save_upload(receipt, "receipts", receipt=True)
        item = HouseholdItem(
            room_id=room.id,
            name=item_name,
            brand=item_brand,
            model=item_model,
            serial_number=item_serial,
            purchase_date=parsed_date,
            replacement_value=parsed_value,
            photo_path=photo_path,
            receipt_path=receipt_path,
            notes=_blank(notes),
        )
        db.add(item)
        db.commit()
        persisted = True
        db.refresh(item)
    except Exception:
        if not persisted:
            db.rollback()
            delete_stored_file(photo_path)
            delete_stored_file(receipt_path)
        raise
    item.room = room
    return item_out(item, _active_loan(db, "item", item.id))


@router.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.scalar(
        select(HouseholdItem).options(selectinload(HouseholdItem.room)).where(
            HouseholdItem.id == item_id
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item_out(item, _active_loan(db, "item", item.id))


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(HouseholdItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    photo_path = item.photo_path
    receipt_path = item.receipt_path
    _delete_loans_for(db, "item", item.id)
    db.delete(item)
    db.commit()
    delete_stored_file(photo_path)
    delete_stored_file(receipt_path)
    return None


@router.get("/borrowers", response_model=list[BorrowerOut])
def list_borrowers(db: Session = Depends(get_db)):
    borrowers = db.scalars(
        select(Borrower).options(selectinload(Borrower.loans).selectinload(Loan.borrower)).order_by(
            Borrower.name
        )
    ).all()
    titles = loan_titles(db, [loan for borrower in borrowers for loan in borrower.loans])
    return [borrower_out(borrower, list(borrower.loans), titles) for borrower in borrowers]


@router.post("/borrowers", response_model=BorrowerOut, status_code=201)
def create_borrower(payload: BorrowerCreate, db: Session = Depends(get_db)):
    borrower = Borrower(name=payload.name, contact=_blank(payload.contact), notes=_blank(payload.notes))
    db.add(borrower)
    db.commit()
    db.refresh(borrower)
    return borrower_out(borrower, [])


@router.get("/borrowers/{borrower_id}", response_model=BorrowerOut)
def get_borrower(borrower_id: int, db: Session = Depends(get_db)):
    borrower = _get_borrower(db, borrower_id)
    titles = loan_titles(db, list(borrower.loans))
    return borrower_out(borrower, list(borrower.loans), titles)


@router.patch("/borrowers/{borrower_id}", response_model=BorrowerOut)
def update_borrower(borrower_id: int, payload: BorrowerUpdate, db: Session = Depends(get_db)):
    borrower = _get_borrower(db, borrower_id)
    if payload.name is not None:
        borrower.name = payload.name
    if payload.contact is not None:
        borrower.contact = _blank(payload.contact)
    if payload.notes is not None:
        borrower.notes = _blank(payload.notes)
    db.commit()
    db.refresh(borrower)
    titles = loan_titles(db, list(borrower.loans))
    return borrower_out(borrower, list(borrower.loans), titles)


@router.delete("/borrowers/{borrower_id}", status_code=204)
def delete_borrower(borrower_id: int, db: Session = Depends(get_db)):
    borrower = _get_borrower(db, borrower_id)
    if any(loan.returned_at is None for loan in borrower.loans):
        raise HTTPException(
            status_code=409,
            detail="Return outstanding loans before removing this borrower",
        )
    db.delete(borrower)
    db.commit()
    return None


@router.get("/loans", response_model=list[LoanOut])
def list_loans(active: bool | None = None, db: Session = Depends(get_db)):
    query = select(Loan).options(selectinload(Loan.borrower)).order_by(Loan.loaned_at.desc(), Loan.id.desc())
    if active is True:
        query = query.where(Loan.returned_at.is_(None))
    elif active is False:
        query = query.where(Loan.returned_at.is_not(None))
    loans = db.scalars(query).all()
    titles = loan_titles(db, list(loans))
    return [loan_out(loan, titles.get((loan.item_kind, loan.item_id))) for loan in loans]


@router.post("/loans", response_model=LoanOut, status_code=201)
def create_loan(payload: LoanCreate, db: Session = Depends(get_db)):
    borrower = db.get(Borrower, payload.borrower_id)
    if not borrower:
        raise HTTPException(status_code=404, detail="Borrower not found")
    title = _loan_item_title(db, payload.item_kind, payload.item_id)
    if _active_loan(db, payload.item_kind, payload.item_id):
        raise HTTPException(status_code=409, detail="This is already on loan")
    loaned_at = payload.loaned_at or date.today()
    if payload.due_date and payload.due_date < loaned_at:
        raise HTTPException(status_code=400, detail="Due date cannot be before the loan date")
    loan = Loan(
        borrower_id=borrower.id,
        item_kind=payload.item_kind,
        item_id=payload.item_id,
        loaned_at=loaned_at,
        due_date=payload.due_date,
        notes=_blank(payload.notes),
    )
    db.add(loan)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This is already on loan") from None
    db.refresh(loan)
    loan.borrower = borrower
    return loan_out(loan, title)


@router.post("/loans/{loan_id}/return", response_model=LoanOut)
def return_loan(loan_id: int, payload: LoanReturn | None = None, db: Session = Depends(get_db)):
    loan = db.scalar(select(Loan).options(selectinload(Loan.borrower)).where(Loan.id == loan_id))
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    if loan.returned_at is not None:
        raise HTTPException(status_code=400, detail="This loan is already returned")
    returned_at = (payload.returned_at if payload else None) or date.today()
    if returned_at < loan.loaned_at:
        raise HTTPException(status_code=400, detail="Returned date cannot be before the loan date")
    loan.returned_at = returned_at
    db.commit()
    db.refresh(loan)
    titles = loan_titles(db, [loan])
    return loan_out(loan, titles.get((loan.item_kind, loan.item_id)))


def _get_borrower(db: Session, borrower_id: int) -> Borrower:
    borrower = db.scalar(
        select(Borrower).options(selectinload(Borrower.loans).selectinload(Loan.borrower)).where(
            Borrower.id == borrower_id
        )
    )
    if not borrower:
        raise HTTPException(status_code=404, detail="Borrower not found")
    return borrower


def _active_loan(db: Session, item_kind: str, item_id: int) -> Loan | None:
    return db.scalar(
        select(Loan)
        .options(selectinload(Loan.borrower))
        .where(
            Loan.item_kind == item_kind,
            Loan.item_id == item_id,
            Loan.returned_at.is_(None),
        )
    )


def _loan_item_title(db: Session, item_kind: str, item_id: int) -> str:
    if item_kind == "book":
        book = db.get(Book, item_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        return book.title
    item = db.get(HouseholdItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item.name


def _delete_loans_for(db: Session, item_kind: str, item_id: int) -> None:
    loans = db.scalars(
        select(Loan).where(Loan.item_kind == item_kind, Loan.item_id == item_id)
    ).all()
    for loan in loans:
        db.delete(loan)


def _blank(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _limited(
    value: str | None,
    *,
    field: str,
    max_length: int,
    required: bool = False,
) -> str | None:
    if value is None:
        if required:
            raise HTTPException(status_code=400, detail=f"{field} is required")
        return None
    stripped = value.strip()
    if required and not stripped:
        raise HTTPException(status_code=400, detail=f"{field} is required")
    if not stripped:
        return None
    if len(stripped) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"{field} must be at most {max_length} characters",
        )
    return stripped


PG_INT_MAX = 2147483647


def _bound_page_count(value: int | None) -> int | None:
    if value is None:
        return None
    if value < 0 or value > PG_INT_MAX:
        raise HTTPException(status_code=400, detail="Page count is out of range")
    return value


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
    if not amount.is_finite():
        raise HTTPException(status_code=400, detail="Replacement value must be a number")
    if amount < 0:
        raise HTTPException(status_code=400, detail="Replacement value cannot be negative")
    try:
        quantized = amount.quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise HTTPException(status_code=400, detail="Replacement value must be a number") from exc
    # Numeric(12, 2) — 10 digits before the decimal, or Postgres raises on commit.
    if quantized > Decimal("9999999999.99"):
        raise HTTPException(status_code=400, detail="Replacement value is too large")
    return quantized


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

