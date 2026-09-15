from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.status import HTTP_303_SEE_OTHER

from app.auth import credentials_ok, is_logged_in
from app.config import settings
from app.db import get_db
from app.models import Book, Borrower, Collection, HouseholdItem, Loan, Room
from app.serializers import (
    active_loans_map,
    book_out,
    borrower_out,
    item_out,
    loan_titles,
    room_out,
)

router = APIRouter()


def templates(request: Request):
    return request.app.state.templates


def workspace_payload(db: Session) -> dict:
    books = db.scalars(select(Book).order_by(Book.created_at.desc())).all()
    rooms = db.scalars(
        select(Room).options(selectinload(Room.items)).order_by(Room.sort_order, Room.name)
    ).all()
    borrowers = db.scalars(
        select(Borrower)
        .options(selectinload(Borrower.loans).selectinload(Loan.borrower))
        .order_by(Borrower.name)
    ).all()
    loans = active_loans_map(db)
    titles = loan_titles(db, [loan for borrower in borrowers for loan in borrower.loans])
    room_payload = []
    total_items = 0
    total_value = Decimal("0")
    for room in rooms:
        data = room_out(room).model_dump(mode="json")
        data["items"] = [
            item_out(item, loans.get(("item", item.id))).model_dump(mode="json")
            for item in room.items
        ]
        room_payload.append(data)
        total_items += data["item_count"]
        total_value += Decimal(str(data["replacement_total"]))
    borrower_payload = [
        borrower_out(borrower, list(borrower.loans), titles).model_dump(mode="json")
        for borrower in borrowers
    ]
    return {
        "books": [
            book_out(book, loans.get(("book", book.id))).model_dump(mode="json")
            for book in books
        ],
        "rooms": room_payload,
        "borrowers": borrower_payload,
        "book_count": len(books),
        "borrower_count": len(borrower_payload),
        "active_loan_count": sum(entry["active_loan_count"] for entry in borrower_payload),
        "total_items": total_items,
        "total_value": f"{total_value:,.2f}",
    }


def render_workspace(
    request: Request,
    db: Session,
    *,
    view: str,
    selected_book_id: int | None = None,
    selected_room_id: int | None = None,
    selected_item_id: int | None = None,
    selected_borrower_id: int | None = None,
):
    context = workspace_payload(db)
    context.update(
        {
            "view": view,
            "selected_book_id": selected_book_id,
            "selected_room_id": selected_room_id,
            "selected_item_id": selected_item_id,
            "selected_borrower_id": selected_borrower_id,
        }
    )
    return templates(request).TemplateResponse(request, "workspace.html", context)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_logged_in(request):
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    return templates(request).TemplateResponse(
        request,
        "login.html",
        {"error": None, "default_user": settings.shelfkeep_username},
    )


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if credentials_ok(username.strip(), password):
        request.session["user"] = settings.shelfkeep_username
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    return templates(request).TemplateResponse(
        request,
        "login.html",
        {"error": "Those credentials were not accepted.", "default_user": username},
        status_code=401,
    )


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)


@router.get("/", response_class=HTMLResponse)
async def library(request: Request, db: Session = Depends(get_db)):
    return render_workspace(request, db, view="library")


@router.get("/books/{book_id}", response_class=HTMLResponse)
async def book_detail(book_id: int, request: Request, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    return render_workspace(request, db, view="library", selected_book_id=book_id)


@router.get("/rooms", response_class=HTMLResponse)
async def rooms_page(request: Request, db: Session = Depends(get_db)):
    payload = workspace_payload(db)
    first_id = payload["rooms"][0]["id"] if payload["rooms"] else None
    return render_workspace(request, db, view="rooms", selected_room_id=first_id)


@router.get("/rooms/{room_id}", response_class=HTMLResponse)
async def room_detail(room_id: int, request: Request, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if not room:
        return RedirectResponse("/rooms", status_code=HTTP_303_SEE_OTHER)
    return render_workspace(request, db, view="room", selected_room_id=room_id)


@router.get("/items/{item_id}", response_class=HTMLResponse)
async def item_detail(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.scalar(
        select(HouseholdItem).options(selectinload(HouseholdItem.room)).where(
            HouseholdItem.id == item_id
        )
    )
    if not item:
        return RedirectResponse("/rooms", status_code=HTTP_303_SEE_OTHER)
    return render_workspace(
        request,
        db,
        view="room",
        selected_room_id=item.room_id,
        selected_item_id=item_id,
    )


@router.get("/borrowers", response_class=HTMLResponse)
async def borrowers_page(request: Request, db: Session = Depends(get_db)):
    return render_workspace(request, db, view="borrowers")


@router.get("/borrowers/{borrower_id}", response_class=HTMLResponse)
async def borrower_detail(borrower_id: int, request: Request, db: Session = Depends(get_db)):
    borrower = db.get(Borrower, borrower_id)
    if not borrower:
        return RedirectResponse("/borrowers", status_code=HTTP_303_SEE_OTHER)
    return render_workspace(request, db, view="borrowers", selected_borrower_id=borrower_id)


def default_collection(db: Session) -> Collection:
    collection = db.scalar(select(Collection).order_by(Collection.id).limit(1))
    if collection:
        return collection
    collection = Collection(name="Library", kind="books")
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection
