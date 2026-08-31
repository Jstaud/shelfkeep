from io import BytesIO

from PIL import Image

from app.config import settings


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (32, 32), (120, 80, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_room_and_item_with_photo_serial_and_value(auth_client):
    room = auth_client.post("/api/rooms", json={"name": "Kitchen", "description": "North side"})
    assert room.status_code == 201
    room_id = room.json()["id"]

    photo = ("kettle.png", _png_bytes(), "image/png")
    item = auth_client.post(
        "/api/items",
        data={
            "room_id": str(room_id),
            "name": "Electric kettle",
            "serial_number": "KTL-42",
            "purchase_date": "2024-03-01",
            "replacement_value": "49.99",
            "notes": "Keep the receipt in the junk drawer.",
        },
        files={"photo": photo},
    )
    assert item.status_code == 201, item.text
    body = item.json()
    assert body["serial_number"] == "KTL-42"
    assert body["replacement_value"] == "49.99"
    assert body["photo_src"]
    assert body["photo_src"].startswith("/media/photos/")

    rooms_page = auth_client.get("/rooms")
    assert rooms_page.status_code == 200
    assert "Kitchen" in rooms_page.text
    assert "$49.99" in rooms_page.text

    room_page = auth_client.get(f"/rooms/{room_id}")
    assert room_page.status_code == 200
    assert "Electric kettle" in room_page.text
    assert "KTL-42" in room_page.text

    media = auth_client.get(body["photo_src"])
    assert media.status_code == 200
    assert media.headers["content-type"].startswith("image/")


def test_invalid_receipt_does_not_leave_orphan_photo(auth_client):
    room = auth_client.post("/api/rooms", json={"name": "Pantry"})
    room_id = room.json()["id"]
    photos_dir = settings.uploads_dir / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    before = {path.name for path in photos_dir.glob("*")}
    response = auth_client.post(
        "/api/items",
        data={"room_id": str(room_id), "name": "Toaster"},
        files={
            "photo": ("toaster.png", _png_bytes(), "image/png"),
            "receipt": ("receipt.png", b"not-a-real-image", "image/png"),
        },
    )
    assert response.status_code == 400
    after = {path.name for path in photos_dir.glob("*")}
    assert after == before


def test_delete_item_removes_photo_from_volume(auth_client):
    room = auth_client.post("/api/rooms", json={"name": "Garage"})
    room_id = room.json()["id"]
    item = auth_client.post(
        "/api/items",
        data={"room_id": str(room_id), "name": "Drill"},
        files={"photo": ("drill.png", _png_bytes(), "image/png")},
    )
    photo_src = item.json()["photo_src"]
    relative = photo_src.removeprefix("/media/")
    stored = settings.uploads_dir / relative
    assert stored.is_file()
    assert auth_client.delete(f"/api/items/{item.json()['id']}").status_code == 204
    assert auth_client.get(photo_src).status_code == 404
    assert not stored.exists()


def test_delete_room_removes_item_uploads(auth_client):
    room = auth_client.post("/api/rooms", json={"name": "Attic"})
    room_id = room.json()["id"]
    item = auth_client.post(
        "/api/items",
        data={"room_id": str(room_id), "name": "Trunk"},
        files={
            "photo": ("trunk.png", _png_bytes(), "image/png"),
            "receipt": ("receipt.png", _png_bytes(), "image/png"),
        },
    )
    body = item.json()
    paths = [settings.uploads_dir / src.removeprefix("/media/") for src in (body["photo_src"], body["receipt_src"])]
    assert all(path.is_file() for path in paths)
    assert auth_client.delete(f"/api/rooms/{room_id}").status_code == 204
    assert auth_client.get(body["photo_src"]).status_code == 404
    assert auth_client.get(body["receipt_src"]).status_code == 404
    assert all(not path.exists() for path in paths)
