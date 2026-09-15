from io import BytesIO

from PIL import Image


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (32, 48), (40, 70, 90)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_manual_movie_disc_and_game_land_on_shelf(auth_client):
    movie = auth_client.post(
        "/api/books",
        json={"title": "Night Train", "authors": "A. Director", "published_year": "1962", "media_type": "movie"},
    )
    assert movie.status_code == 201, movie.text
    assert movie.json()["media_type"] == "movie"
    assert movie.json()["authors"] == "A. Director"

    disc = auth_client.post(
        "/api/books",
        json={"title": "Blue Note Set", "authors": "A Quartet", "media_type": "disc"},
    )
    assert disc.status_code == 201
    assert disc.json()["media_type"] == "disc"

    game = auth_client.post(
        "/api/books",
        json={"title": "Tabletop Atlas", "authors": "Local Studio", "media_type": "game", "notes": "Box in the attic"},
    )
    assert game.status_code == 201
    assert game.json()["media_type"] == "game"

    listed = auth_client.get("/api/books")
    types = {row["title"]: row["media_type"] for row in listed.json()}
    assert types["Night Train"] == "movie"
    assert types["Blue Note Set"] == "disc"
    assert types["Tabletop Atlas"] == "game"

    movies = auth_client.get("/api/books", params={"media_type": "movie"})
    assert movies.status_code == 200
    assert [row["title"] for row in movies.json()] == ["Night Train"]

    page = auth_client.get("/")
    assert page.status_code == 200
    assert "Night Train" in page.text
    assert 'data-media-filter="movie"' in page.text
    assert "Add a movie" in page.text or "Movies" in page.text


def test_invalid_media_type_is_rejected(auth_client):
    response = auth_client.post("/api/books", json={"title": "Mystery", "media_type": "vhs"})
    assert response.status_code == 422


def test_books_default_to_book_type(auth_client):
    created = auth_client.post("/api/books", json={"title": "Still a Book"})
    assert created.status_code == 201
    assert created.json()["media_type"] == "book"


def test_edit_catalog_item_and_upload_cover(auth_client):
    created = auth_client.post(
        "/api/books",
        json={"title": "Draft Reel", "media_type": "movie"},
    )
    book_id = created.json()["id"]
    updated = auth_client.put(
        f"/api/books/{book_id}",
        json={"title": "Final Reel", "authors": "B. Director", "published_year": "1977", "media_type": "movie"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Final Reel"
    assert updated.json()["authors"] == "B. Director"
    assert updated.json()["media_type"] == "movie"

    cover = auth_client.post(
        f"/api/books/{book_id}/cover",
        files={"cover": ("reel.png", _png_bytes(), "image/png")},
    )
    assert cover.status_code == 200, cover.text
    assert cover.json()["cover_src"]
    assert cover.json()["cover_src"].startswith("/media/covers/")
    media = auth_client.get(cover.json()["cover_src"])
    assert media.status_code == 200


def test_media_type_filter_rejects_unknown(auth_client):
    response = auth_client.get("/api/books", params={"media_type": "vhs"})
    assert response.status_code == 400
