from pathlib import Path
from urllib.parse import unquote

from app.config import (
    INSECURE_SESSION_SECRETS,
    SESSION_SECRET_FILENAME,
    postgres_database_url,
    resolve_session_secret,
)


def test_whitespace_only_title_is_rejected(auth_client):
    response = auth_client.post("/api/books", json={"title": "   "})
    assert response.status_code == 422


def test_whitespace_only_room_name_is_rejected(auth_client):
    response = auth_client.post("/api/rooms", json={"name": "\t  "})
    assert response.status_code == 422


def test_page_count_rejects_integer_overflow(auth_client):
    for bad in (2_147_483_648, -1, 10**12):
        response = auth_client.post(
            "/api/books",
            json={"title": "Overlong Folio", "page_count": bad},
        )
        assert response.status_code == 400, bad
        assert "page count" in response.json()["detail"].lower()
    ok = auth_client.post(
        "/api/books",
        json={"title": "Short Folio", "page_count": 2147483647},
    )
    assert ok.status_code == 201, ok.text


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


def test_replacement_value_rejects_numeric_12_2_overflow(auth_client):
    room = auth_client.post("/api/rooms", json={"name": "Vault"})
    room_id = room.json()["id"]
    for bad in ("10000000000.00", "99999999999", "1e12"):
        response = auth_client.post(
            "/api/items",
            data={"room_id": str(room_id), "name": "Safe", "replacement_value": bad},
        )
        assert response.status_code == 400, bad
        assert "too large" in response.json()["detail"].lower()
    ok = auth_client.post(
        "/api/items",
        data={"room_id": str(room_id), "name": "Watch", "replacement_value": "9999999999.99"},
    )
    assert ok.status_code == 201, ok.text


def test_item_string_fields_respect_column_limits(auth_client):
    room = auth_client.post("/api/rooms", json={"name": "Study"})
    room_id = room.json()["id"]
    cases = (
        ("name", "x" * 301, "Name"),
        ("brand", "b" * 201, "Brand"),
        ("model", "m" * 201, "Model"),
        ("serial_number", "s" * 201, "Serial number"),
    )
    for field, value, label in cases:
        data = {"room_id": str(room_id), "name": "Lamp"}
        data[field] = value
        response = auth_client.post("/api/items", data=data)
        assert response.status_code == 400, field
        assert label.lower() in response.json()["detail"].lower()


def test_placeholder_session_secret_is_not_used(tmp_path: Path):
    for placeholder in INSECURE_SESSION_SECRETS:
        stored_dir = tmp_path / (placeholder or "empty")
        first = resolve_session_secret(placeholder, stored_dir)
        assert first not in INSECURE_SESSION_SECRETS
        assert len(first) >= 32
        persisted = stored_dir / SESSION_SECRET_FILENAME
        assert persisted.read_text(encoding="utf-8") == first
        again = resolve_session_secret("replace-with-a-long-random-string", stored_dir)
        assert again == first


def test_compose_does_not_ship_a_public_session_secret():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    example = Path(".env.example").read_text(encoding="utf-8")
    for leaked in ("change-this-session-secret", "replace-with-a-long-random-string"):
        assert leaked not in compose
        assert leaked not in example


def test_explicit_session_secret_is_kept(tmp_path: Path):
    assert resolve_session_secret("unique-operator-secret", tmp_path) == "unique-operator-secret"
    assert not (tmp_path / SESSION_SECRET_FILENAME).exists()


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
