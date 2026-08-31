from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.status import HTTP_303_SEE_OTHER

from app.auth import credentials_ok, is_logged_in
from app.config import settings
from app.db import get_db
from app.models import Book, Collection, HouseholdItem, Room
from app.serializers import book_out, item_out, room_out

router = APIRouter()


def templates(request: Request):
    return request.app.state.templates


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
    books = db.scalars(select(Book).order_by(Book.created_at.desc())).all()
    return templates(request).TemplateResponse(
        request,
        "library.html",
        {
            "books": [book_out(b).model_dump(mode="json") for b in books],
            "book_count": len(books),
        },
    )


@router.get("/books/{book_id}", response_class=HTMLResponse)
async def book_detail(book_id: int, request: Request, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    return templates(request).TemplateResponse(
        request,
        "book_detail.html",
        {"book": book_out(book).model_dump(mode="json")},
    )


@router.get("/rooms", response_class=HTMLResponse)
async def rooms_page(request: Request, db: Session = Depends(get_db)):
    rooms = db.scalars(
        select(Room).options(selectinload(Room.items)).order_by(Room.sort_order, Room.name)
    ).all()
    room_payload = [room_out(r).model_dump(mode="json") for r in rooms]
    total_items = sum(r["item_count"] for r in room_payload)
    total_value = sum(Decimal(str(r["replacement_total"])) for r in room_payload)
    return templates(request).TemplateResponse(
        request,
        "rooms.html",
        {
            "rooms": room_payload,
            "total_items": total_items,
            "total_value": f"{total_value:,.2f}",
        },
    )


@router.get("/rooms/{room_id}", response_class=HTMLResponse)
async def room_detail(room_id: int, request: Request, db: Session = Depends(get_db)):
    room = db.scalar(
        select(Room).options(selectinload(Room.items)).where(Room.id == room_id)
    )
    if not room:
        return RedirectResponse("/rooms", status_code=HTTP_303_SEE_OTHER)
    items = [item_out(i).model_dump(mode="json") for i in room.items]
    payload = room_out(room).model_dump(mode="json")
    return templates(request).TemplateResponse(
        request,
        "room_detail.html",
        {"room": payload, "items": items},
    )


@router.get("/items/{item_id}", response_class=HTMLResponse)
async def item_detail(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.scalar(
        select(HouseholdItem).options(selectinload(HouseholdItem.room)).where(
            HouseholdItem.id == item_id
        )
    )
    if not item:
        return RedirectResponse("/rooms", status_code=HTTP_303_SEE_OTHER)
    return templates(request).TemplateResponse(
        request,
        "item_detail.html",
        {"item": item_out(item).model_dump(mode="json")},
    )


def default_collection(db: Session) -> Collection:
    collection = db.scalar(select(Collection).order_by(Collection.id).limit(1))
    if collection:
        return collection
    collection = Collection(name="Library", kind="books")
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


