from io import BytesIO

from PIL import Image


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
