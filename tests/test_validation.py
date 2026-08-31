from urllib.parse import unquote

from app.config import postgres_database_url


def test_whitespace_only_title_is_rejected(auth_client):
    response = auth_client.post("/api/books", json={"title": "   "})
    assert response.status_code == 422


def test_whitespace_only_room_name_is_rejected(auth_client):
    response = auth_client.post("/api/rooms", json={"name": "\t  "})
    assert response.status_code == 422


def test_replacement_value_rejects_nan_and_infinity(auth_client):
    room = auth_client.post("/api/rooms", json={"name": "Workshop"})
    room_id = room.json()["id"]
    for bad in ("NaN", "Infinity", "-Infinity", "1e999999"):
        response = auth_client.post(
            "/api/items",
            data={"room_id": str(room_id), "name": "Lamp", "replacement_value": bad},
        )
        assert response.status_code == 400, bad
        assert "number" in response.json()["detail"].lower()


def test_postgres_url_encodes_reserved_password_characters():
    url = postgres_database_url(
        user="keep/user",
        password="p@ss/word#1?x",
        host="db",
        database="shelf/keep",
    )
    assert "p@ss/word" not in url
    assert "p%40ss%2Fword%231%3Fx" in url
    assert "keep%2Fuser" in url
    assert "shelf%2Fkeep" in url
    user, rest = url.removeprefix("postgresql+psycopg://").split("@", 1)
    name, password = user.split(":", 1)
    assert unquote(name) == "keep/user"
    assert unquote(password) == "p@ss/word#1?x"
    assert rest.startswith("db:5432/")
