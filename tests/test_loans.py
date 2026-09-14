from datetime import date, timedelta

from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import Loan


def _book(auth_client, title="Loaned Atlas"):
    response = auth_client.post("/api/books", json={"title": title, "media_type": "book"})
    assert response.status_code == 201
    return response.json()


def _item(auth_client, name="Loaned Kettle"):
    room = auth_client.post("/api/rooms", json={"name": "Lending pantry"})
    assert room.status_code == 201
    item = auth_client.post(
        "/api/items",
        data={"room_id": str(room.json()["id"]), "name": name},
    )
    assert item.status_code == 201
    return item.json()


def _borrower(auth_client, name="Alex", contact="alex@home"):
    response = auth_client.post(
        "/api/borrowers",
        json={"name": name, "contact": contact, "notes": "Neighbor"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_borrower_crud_and_workspace_nav(auth_client):
    created = _borrower(auth_client, name="Sam", contact="555-0199")
    assert created["name"] == "Sam"
    assert created["contact"] == "555-0199"
    assert created["active_loan_count"] == 0

    listed = auth_client.get("/api/borrowers")
    assert any(row["name"] == "Sam" for row in listed.json())

    page = auth_client.get("/borrowers")
    assert page.status_code == 200
    assert "Sam" in page.text
    assert "Borrowers" in page.text
    assert "Out now" in page.text

    patched = auth_client.patch(f"/api/borrowers/{created['id']}", json={"contact": "555-0100"})
    assert patched.status_code == 200
    assert patched.json()["contact"] == "555-0100"

    assert auth_client.delete(f"/api/borrowers/{created['id']}").status_code == 204
    assert auth_client.get(f"/api/borrowers/{created['id']}").status_code == 404


def test_loan_book_and_mark_returned(auth_client):
    book = _book(auth_client, "Field Guide")
    person = _borrower(auth_client, name="Jordan")
    loaned_at = date.today().isoformat()
    due = (date.today() + timedelta(days=14)).isoformat()
    loan = auth_client.post(
        "/api/loans",
        json={
            "borrower_id": person["id"],
            "item_kind": "book",
            "item_id": book["id"],
            "loaned_at": loaned_at,
            "due_date": due,
        },
    )
    assert loan.status_code == 201, loan.text
    body = loan.json()
    assert body["borrower_name"] == "Jordan"
    assert body["item_title"] == "Field Guide"
    assert body["returned_at"] is None

    fetched = auth_client.get(f"/api/books/{book['id']}")
    assert fetched.json()["loan"]["borrower_name"] == "Jordan"
    assert fetched.json()["loan"]["due_date"] == due

    second = auth_client.post(
        "/api/loans",
        json={"borrower_id": person["id"], "item_kind": "book", "item_id": book["id"]},
    )
    assert second.status_code == 409

    returned = auth_client.post(f"/api/loans/{body['id']}/return", json={})
    assert returned.status_code == 200
    assert returned.json()["returned_at"] == date.today().isoformat()
    assert auth_client.get(f"/api/books/{book['id']}").json()["loan"] is None

    again = auth_client.post(f"/api/loans/{body['id']}/return", json={})
    assert again.status_code == 400

    relend = auth_client.post(
        "/api/loans",
        json={"borrower_id": person["id"], "item_kind": "book", "item_id": book["id"]},
    )
    assert relend.status_code == 201, relend.text


def test_loan_household_item(auth_client):
    item = _item(auth_client, "Stand mixer")
    person = _borrower(auth_client, name="Riley")
    loan = auth_client.post(
        "/api/loans",
        json={"borrower_id": person["id"], "item_kind": "item", "item_id": item["id"]},
    )
    assert loan.status_code == 201, loan.text
    assert loan.json()["item_title"] == "Stand mixer"
    fetched = auth_client.get(f"/api/items/{item['id']}")
    assert fetched.json()["loan"]["borrower_name"] == "Riley"


def test_cannot_remove_borrower_with_active_loan(auth_client):
    book = _book(auth_client, "Keep this")
    person = _borrower(auth_client, name="Casey")
    loan = auth_client.post(
        "/api/loans",
        json={"borrower_id": person["id"], "item_kind": "book", "item_id": book["id"]},
    )
    assert loan.status_code == 201
    blocked = auth_client.delete(f"/api/borrowers/{person['id']}")
    assert blocked.status_code == 409

    assert auth_client.post(f"/api/loans/{loan.json()['id']}/return", json={}).status_code == 200
    assert auth_client.delete(f"/api/borrowers/{person['id']}").status_code == 204


def test_due_date_before_loan_date_is_rejected(auth_client):
    book = _book(auth_client, "Calendar")
    person = _borrower(auth_client, name="Drew")
    response = auth_client.post(
        "/api/loans",
        json={
            "borrower_id": person["id"],
            "item_kind": "book",
            "item_id": book["id"],
            "loaned_at": "2026-09-10",
            "due_date": "2026-09-01",
        },
    )
    assert response.status_code == 400


def test_delete_book_clears_its_loans(auth_client):
    book = _book(auth_client, "Vanishing")
    person = _borrower(auth_client, name="Morgan")
    loan = auth_client.post(
        "/api/loans",
        json={"borrower_id": person["id"], "item_kind": "book", "item_id": book["id"]},
    )
    assert loan.status_code == 201
    assert auth_client.delete(f"/api/books/{book['id']}").status_code == 204
    assert auth_client.get(f"/api/loans/{loan.json()['id']}", follow_redirects=False).status_code in {404, 405}
    leftover = auth_client.get("/api/loans")
    assert leftover.status_code == 200
    assert all(row["id"] != loan.json()["id"] for row in leftover.json())


def test_active_loan_unique_index_blocks_direct_insert(auth_client):
    book = _book(auth_client, "Double Out")
    person = _borrower(auth_client, name="Quinn")
    loan = auth_client.post(
        "/api/loans",
        json={"borrower_id": person["id"], "item_kind": "book", "item_id": book["id"]},
    )
    assert loan.status_code == 201
    db = SessionLocal()
    try:
        db.add(
            Loan(
                borrower_id=person["id"],
                item_kind="book",
                item_id=book["id"],
                loaned_at=date.today(),
            )
        )
        db.commit()
        raise AssertionError("second active loan should violate uq_loans_active_item")
    except IntegrityError:
        db.rollback()
    finally:
        db.close()


def test_whitespace_only_borrower_name_is_rejected(auth_client):
    response = auth_client.post("/api/borrowers", json={"name": "   "})
    assert response.status_code == 422
