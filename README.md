# Shelfkeep

Self-hosted catalog for the things you keep: a library you browse like a room, and a home inventory that is useful when you need it.

Add a book by ISBN, title, or by hand and see it on a wooden shelf with cover art. Walk rooms, photograph household items, and keep serial numbers, purchase dates, replacement values, and receipts — insurance-friendly without becoming a spreadsheet.

Shelfkeep is a web app (responsive, installable as a PWA). It is not Mac-only. `docker compose up` is the happy path. There is no required cloud account.

## Why

Physical collections and household stuff are the same problem: you want to *see* what you have, not row through a grid. Shelfkeep keeps the tactile, cover-forward feeling of a personal library and extends it to the rest of the house.

## Non-affiliation

**Shelfkeep is original open-source software.** It is **not** affiliated with, endorsed by, or a substitute product of Delicious Monster, Delicious Library, or Under My Roof. We do not copy their trademarks, artwork, copy, or proprietary library formats.

The interface is inspired by the *feeling* of browsing real shelves — not a clone of any commercial app.

## Features (v1)

- Three-pane workspace: collections and rooms on the left, a shelf of object-like covers in the center, details on the right
- Wooden-shelf library with large cover art (sheen, spine, and shadow — original, not a clone)
- Add books by ISBN, title lookup, or manual entry
- Public metadata from [Open Library](https://openlibrary.org) (covers and bibliographic data), with a graceful fallback if lookup fails
- Optional on-device barcode scan in browsers that implement `BarcodeDetector` (Chromium)
- Rooms and household items with photo upload, serial, purchase date, replacement value, and receipts
- Single-user local login (username and password from environment)
- PWA manifest and a small offline app-shell cache
- Postgres + persisted volumes via Docker Compose

## Run locally

### Docker Compose (recommended)

You need Docker and Docker Compose.

```bash
cp .env.example .env
# Edit .env: set SHELFKEEP_PASSWORD. Leave SESSION_SECRET blank to generate one.
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080) and sign in with `SHELFKEEP_USERNAME` / `SHELFKEEP_PASSWORD` (defaults in `.env.example` are `admin` / `changeme`).

Data lives in Docker volumes:

- `db_data` — PostgreSQL
- `uploads` — cover art, item photos, receipts

Stop with `Ctrl+C`, or `docker compose down`. Volumes persist until you `docker compose down -v`.

### Without Docker

Python 3.12+ is enough. Shelfkeep will use SQLite under `./data` if `DATABASE_URL` is unset.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export SHELFKEEP_USERNAME=admin
export SHELFKEEP_PASSWORD=changeme
export SESSION_SECRET=dev-only-secret
uvicorn app.main:app --reload --port 8080
```

### Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Configuration

| Variable | Purpose |
| --- | --- |
| `SHELFKEEP_USERNAME` | Local login name (default `admin`) |
| `SHELFKEEP_PASSWORD` | Local login password (change this) |
| `SESSION_SECRET` | Cookie signing key. If unset or a documented placeholder, a unique key is generated and persisted under `DATA_DIR` |
| `DATABASE_URL` | SQLAlchemy URL for non-Docker runs. Compose does not set this; the app builds an encoded URL from `POSTGRES_HOST` + `POSTGRES_*` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Compose Postgres credentials (URL-encoded by the app) |
| `DATA_DIR` | Where uploads are stored (Compose: `/data`) |
| `SESSION_HTTPS_ONLY` | Set `true` if you terminate TLS in front of the app |

The process logs a warning if the default login password is still in use. A missing or placeholder `SESSION_SECRET` is never used to sign cookies.

## Stack

Boring on purpose: **FastAPI**, **SQLAlchemy**, **PostgreSQL** (SQLite for tests / no-Docker), vanilla HTML/CSS/JS, Docker Compose. No Kubernetes, no cloud account, no extra JS build step.

Book lookup uses documented Open Library APIs:

- `https://openlibrary.org/api/books` (ISBN → metadata)
- `https://openlibrary.org/search.json` (title search)
- `https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false` (cover art)

If Open Library is unreachable or has no record, you can still file the book by hand. A cloth-bound placeholder is shown when there is no cover.

## Out of scope (for now)

- Native mobile apps (the PWA is the install path)
- Multi-tenant SaaS
- Amazon (or other retailer) scraping
- Importing proprietary Delicious Library libraries

Those are future work, not part of this first slice.

## License

[MIT](LICENSE).
