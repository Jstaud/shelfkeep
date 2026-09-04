# Changelog

Shelfkeep versions follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Do not create a git tag from a packaging PR. Tagging stays with the
maintainer after merge.

## [Unreleased]

### Added

- GitHub Actions publishes `ghcr.io/jstaud/shelfkeep` on `v*` tags (also
  `latest`) and on `main`. Compose can pull that image via `SHELFKEEP_IMAGE`
  instead of `up --build`.
- Linux (`ubuntu-latest`, x86_64) and macOS (`macos-latest`, arm64) PyInstaller
  binaries attached to GitHub Releases on `v*` tags. `workflow_dispatch` can
  attach assets to an existing tag such as `v1.0.0`.
- `shelfkeep` / `shelfkeep serve` CLI: binds `127.0.0.1:8080` by default,
  SQLite under a user-writable `DATA_DIR`, same env vars as Compose.
- README install options: Compose (primary), GHCR image, Linux/macOS binary.

## [1.0.0] - 2026-09-04

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

[Unreleased]: https://github.com/Jstaud/shelfkeep/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Jstaud/shelfkeep/releases/tag/v1.0.0
