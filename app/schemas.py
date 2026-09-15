from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


def _required_text(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("This field cannot be blank")
    return stripped


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


MEDIA_TYPES = ("book", "movie", "disc", "game")
LOAN_ITEM_KINDS = ("book", "item")


def _media_type(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in MEDIA_TYPES:
        raise ValueError("media_type must be book, movie, disc, or game")
    return normalized


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    subtitle: str | None = Field(default=None, max_length=500)
    media_type: str = "book"

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        return _required_text(value)

    @field_validator("media_type")
    @classmethod
    def media_type_allowed(cls, value: str) -> str:
        return _media_type(value)
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


class LoanBrief(BaseModel):
    id: int
    borrower_id: int
    borrower_name: str
    loaned_at: date
    due_date: date | None


class BookOut(BaseModel):
    id: int
    collection_id: int
    media_type: str = "book"
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
    loan: LoanBrief | None = None

    model_config = {"from_attributes": True}


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        return _required_text(value)


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
    loan: LoanBrief | None = None

    model_config = {"from_attributes": True}


class BorrowerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    contact: str | None = Field(default=None, max_length=300)
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        return _required_text(value)


class BorrowerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    contact: str | None = Field(default=None, max_length=300)
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _required_text(value)


class LoanCreate(BaseModel):
    borrower_id: int
    item_kind: str
    item_id: int
    loaned_at: date | None = None
    due_date: date | None = None
    notes: str | None = None

    @field_validator("item_kind")
    @classmethod
    def item_kind_allowed(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in LOAN_ITEM_KINDS:
            raise ValueError("item_kind must be book or item")
        return normalized


class LoanReturn(BaseModel):
    returned_at: date | None = None


class LoanOut(BaseModel):
    id: int
    borrower_id: int
    borrower_name: str
    item_kind: str
    item_id: int
    item_title: str | None = None
    loaned_at: date
    due_date: date | None
    returned_at: date | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BorrowerOut(BaseModel):
    id: int
    name: str
    contact: str | None
    notes: str | None
    active_loan_count: int = 0
    loans: list[LoanOut] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}
