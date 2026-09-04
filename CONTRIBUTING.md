# Contributing

Thanks for looking. Shelfkeep is original MIT-licensed software. Keep it that
way.

## Ground rules

- **MIT.** New files should be compatible with [LICENSE](LICENSE). Do not add
  a copyleft or proprietary dependency without a discussion first.
- **Not affiliated** with Delicious Monster, Delicious Library, or Under My
  Roof. Do not copy their trademarks, word marks, artwork, copy, icons, or
  proprietary library formats. The UI is original — inspired by the *feeling*
  of real shelves, not a clone of any commercial app.
- **Self-hosted.** Do not add a required cloud account or a Kubernetes
  manifest. `docker compose up --build` stays enough. The GHCR image and
  release binaries are optional; they must not become a required cloud
  account for end users.
- **Open Library only** for book lookup. No Amazon (or other retailer)
  scraping, and no import of proprietary Delicious Library libraries.

## How to work

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

Match existing style: FastAPI + SQLAlchemy, vanilla HTML/CSS/JS, no extra
frontend build step. Keep `.env.example` free of real secrets. Leave
`SESSION_SECRET` blank so a unique key is generated.

Open a pull request against `main` with a short description of the change.
CI runs `pytest`. Keep it green.
