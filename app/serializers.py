from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Book, Borrower, HouseholdItem, Loan, Room
from app.schemas import BookOut, BorrowerOut, ItemOut, LoanBrief, LoanOut, RoomOut
from app.uploads import media_url


def active_loans_map(db: Session) -> dict[tuple[str, int], Loan]:
    loans = db.scalars(
        select(Loan).options(selectinload(Loan.borrower)).where(Loan.returned_at.is_(None))
    ).all()
    return {(loan.item_kind, loan.item_id): loan for loan in loans}


def loan_titles(db: Session, loans: list[Loan]) -> dict[tuple[str, int], str]:
    book_ids = [loan.item_id for loan in loans if loan.item_kind == "book"]
    item_ids = [loan.item_id for loan in loans if loan.item_kind == "item"]
    titles: dict[tuple[str, int], str] = {}
    if book_ids:
        for book in db.scalars(select(Book).where(Book.id.in_(book_ids))):
            titles[("book", book.id)] = book.title
    if item_ids:
        for item in db.scalars(select(HouseholdItem).where(HouseholdItem.id.in_(item_ids))):
            titles[("item", item.id)] = item.name
    return titles


def loan_brief(loan: Loan) -> LoanBrief:
    return LoanBrief(
        id=loan.id,
        borrower_id=loan.borrower_id,
        borrower_name=loan.borrower.name if loan.borrower else "",
        loaned_at=loan.loaned_at,
        due_date=loan.due_date,
    )


def loan_out(loan: Loan, item_title: str | None = None) -> LoanOut:
    return LoanOut(
        id=loan.id,
        borrower_id=loan.borrower_id,
        borrower_name=loan.borrower.name if loan.borrower else "",
        item_kind=loan.item_kind,
        item_id=loan.item_id,
        item_title=item_title,
        loaned_at=loan.loaned_at,
        due_date=loan.due_date,
        returned_at=loan.returned_at,
        notes=loan.notes,
        created_at=loan.created_at,
    )


def borrower_out(
    borrower: Borrower,
    loans: list[Loan] | None = None,
    titles: dict[tuple[str, int], str] | None = None,
) -> BorrowerOut:
    loan_models = list(borrower.loans or []) if loans is None else list(loans)
    loan_models.sort(key=lambda loan: (loan.returned_at is not None, loan.loaned_at), reverse=False)
    titles = titles or {}
    return BorrowerOut(
        id=borrower.id,
        name=borrower.name,
        contact=borrower.contact,
        notes=borrower.notes,
        active_loan_count=sum(1 for loan in loan_models if loan.returned_at is None),
        loans=[
            loan_out(loan, titles.get((loan.item_kind, loan.item_id))) for loan in loan_models
        ],
        created_at=borrower.created_at,
    )


def book_out(book: Book, loan: Loan | None = None) -> BookOut:
    return BookOut(
        id=book.id,
        collection_id=book.collection_id,
        media_type=book.media_type or "book",
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
        loan=loan_brief(loan) if loan else None,
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


def item_out(item: HouseholdItem, loan: Loan | None = None) -> ItemOut:
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
        loan=loan_brief(loan) if loan else None,
    )
