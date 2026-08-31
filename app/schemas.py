from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class BookLookup(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    authors: str | None = None
    isbn: str | None = None
    publisher: str | None = None
    published_year: str | None = None
    page_count: int | None = None
    description: str | None = None
    cover_url: str | None = None
    openlibrary_url: str | None = None
    source: str = "openlibrary"


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    subtitle: str | None = Field(default=None, max_length=500)
    authors: str | None = Field(default=None, max_length=500)
    isbn: str | None = Field(default=None, max_length=32)
    publisher: str | None = Field(default=None, max_length=300)
    published_year: str | None = Field(default=None, max_length=20)
    page_count: int | None = None
    description: str | None = None
    cover_url: str | None = Field(default=None, max_length=800)
    openlibrary_url: str | None = Field(default=None, max_length=400)
    notes: str | None = None
    collection_id: int | None = None


class BookOut(BaseModel):
    id: int
    collection_id: int
    title: str
    subtitle: str | None
    authors: str | None
    isbn: str | None
    publisher: str | None
    published_year: str | None
    page_count: int | None
    description: str | None
    cover_url: str | None
    cover_src: str | None
    openlibrary_url: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)


class RoomOut(BaseModel):
    id: int
    name: str
    description: str | None
    item_count: int = 0
    replacement_total: Decimal = Decimal("0")
    created_at: datetime

    model_config = {"from_attributes": True}


class ItemCreate(BaseModel):
    room_id: int
    name: str = Field(min_length=1, max_length=300)
    brand: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)
    serial_number: str | None = Field(default=None, max_length=200)
    purchase_date: date | None = None
    replacement_value: Decimal | None = None
    notes: str | None = None


class ItemOut(BaseModel):
    id: int
    room_id: int
    room_name: str | None = None
    name: str
    brand: str | None
    model: str | None
    serial_number: str | None
    purchase_date: date | None
    replacement_value: Decimal | None
    photo_src: str | None
    receipt_src: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
