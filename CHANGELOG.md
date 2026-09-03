# Changelog

Shelfkeep versions follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The `v1.0.0` git tag is created **after** this changelog lands on `main`.
Do not tag from a docs PR.

## [1.0.0] — 2026-09-03

First public release. Self-hosted catalog for books and household stuff.
No cloud account, no Kubernetes, no registry image required.

### Added

- Three-pane workspace: collections and rooms on the left, a wooden shelf of
  object-like covers in the center, details in the right inspector
- Library: add a book by ISBN, title, or by hand
- Book metadata and covers from [Open Library](https://openlibrary.org) only,
  with a cloth-bound placeholder if lookup fails
- Optional on-device barcode scan where `BarcodeDetector` is available
- Rooms and household items: photo, serial, purchase date, replacement value,
  receipt
- Single-user local login (`SHELFKEEP_USERNAME` / `SHELFKEEP_PASSWORD`)
- Unique `SESSION_SECRET`: empty or documented placeholders are refused;
  a key is generated and persisted under `DATA_DIR`
- PWA manifest and a small offline app-shell cache
- Docker Compose happy path (`postgres:16-alpine` + the app, persisted volumes)
- SQLite fallback when `DATABASE_URL` is unset (no-Docker / tests)
- MIT license, with an explicit non-affiliation notice for Delicious Monster,
  Delicious Library, and Under My Roof

### Security

- Default password `changeme` logs a warning at boot
- `.env.example` ships empty `SESSION_SECRET` and no real secrets
- Uploaded files stay on local volumes; nothing is sent to a third-party
  store (covers are fetched from Open Library and cached locally)

The `v1.0.0` release tag is cut from `main` after merge — not from this
changelog commit.
