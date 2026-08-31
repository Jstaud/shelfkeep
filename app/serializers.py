from decimal import Decimal

from app.models import Book, HouseholdItem, Room
from app.schemas import BookOut, ItemOut, RoomOut
from app.uploads import media_url


def book_out(book: Book) -> BookOut:
    return BookOut(
        id=book.id,
        collection_id=book.collection_id,
        title=book.title,
        subtitle=book.subtitle,
        authors=book.authors,
        isbn=book.isbn,
        publisher=book.publisher,
        published_year=book.published_year,
        page_count=book.page_count,
        description=book.description,
        cover_url=book.cover_url,
        cover_src=media_url(book.cover_path) or book.cover_url,
        openlibrary_url=book.openlibrary_url,
        notes=book.notes,
        created_at=book.created_at,
    )


def room_out(room: Room) -> RoomOut:
    items = room.items or []
    total = sum((item.replacement_value or Decimal("0")) for item in items)
    return RoomOut(
        id=room.id,
        name=room.name,
        description=room.description,
        item_count=len(items),
        replacement_total=total,
        created_at=room.created_at,
    )


def item_out(item: HouseholdItem) -> ItemOut:
    return ItemOut(
        id=item.id,
        room_id=item.room_id,
        room_name=item.room.name if item.room else None,
        name=item.name,
        brand=item.brand,
        model=item.model,
        serial_number=item.serial_number,
        purchase_date=item.purchase_date,
        replacement_value=item.replacement_value,
        photo_src=media_url(item.photo_path),
        receipt_src=media_url(item.receipt_path),
        notes=item.notes,
        created_at=item.created_at,
    )
