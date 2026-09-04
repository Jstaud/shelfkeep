Shelfkeep — self-hosted catalog

This archive is a packaged binary. You do not need Docker or Python.

Quick start
-----------
  chmod +x shelfkeep
  ./shelfkeep

Or install to ~/.local/bin:
  ./install.sh

Then open http://127.0.0.1:8080 and sign in (default admin / changeme).
Set SHELFKEEP_PASSWORD before you expose the process beyond this machine.

Data
----
Linux:   ~/.local/share/shelfkeep
macOS:   ~/Library/Application Support/shelfkeep
Override with DATA_DIR. SQLite is the default database (shelfkeep.db in
that directory). Optional Postgres:

  export DATABASE_URL=postgresql+psycopg://user:pass@host:5432/shelfkeep

Environment (same names as the README)
--------------------------------------
  SHELFKEEP_USERNAME   login name (default admin)
  SHELFKEEP_PASSWORD   login password (default changeme — change this)
  SESSION_SECRET       cookie key; blank generates and persists one
  DATA_DIR             uploads + generated session secret
  DATABASE_URL         optional Postgres (or another SQLAlchemy URL)
  SHELFKEEP_HOST       bind address (default 127.0.0.1)
  SHELFKEEP_PORT       bind port (default 8080)

  shelfkeep --help
  shelfkeep serve --host 127.0.0.1 --port 8080

macOS Gatekeeper
----------------
This build is not signed with an Apple Developer ID. After download,
macOS may say the app "cannot be opened because it is from an unidentified
developer." That is expected without a paid signing certificate.

  1. Right-click the binary → Open → Open, or
  2. xattr -d com.apple.quarantine ./shelfkeep

CI currently publishes an Apple Silicon (arm64) binary from the macos-15
runner. That asset is arm64-only and does not run on Intel Macs. An Intel
release job is not in this slice — on Intel, build from source with
PyInstaller (packaging/shelfkeep.spec).

License: MIT. Compose + Postgres remains the documented happy path.
See https://github.com/Jstaud/shelfkeep
