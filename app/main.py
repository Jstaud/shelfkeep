from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app import __version__
from app.auth import AuthGateMiddleware
from app.config import settings
from app.db import Base, engine, get_db
from app.models import Collection
from app.routers import api, pages
from app.uploads import ensure_dirs, safe_join

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("shelfkeep")

APP_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    ensure_dirs()
    _wait_for_database()
    Base.metadata.create_all(bind=engine)
    _seed_library()
    if settings.using_default_secrets:
        log.warning(
            "Default login password is in use. "
            "Set SHELFKEEP_PASSWORD before exposing this instance."
        )
    yield


def _wait_for_database(attempts: int = 20) -> None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001 - retry any connect failure at boot
            last_error = exc
            log.warning("Database not ready (attempt %s/%s): %s", attempt, attempts, exc)
            time.sleep(1)
    raise RuntimeError("Could not connect to the database") from last_error


def _seed_library() -> None:
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        existing = db.scalar(select(Collection).limit(1))
        if not existing:
            db.add(Collection(name="Library", kind="books"))
            db.commit()
    finally:
        db.close()


app = FastAPI(
    title="Shelfkeep",
    version=__version__,
    description="Self-hosted catalog and home inventory.",
    lifespan=lifespan,
)

app.add_middleware(AuthGateMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.resolved_session_secret,
    session_cookie="shelfkeep_session",
    same_site="lax",
    https_only=settings.session_https_only,
    max_age=60 * 60 * 24 * 30,
)

app.state.templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

app.include_router(pages.router)
app.include_router(api.router)


@app.get("/healthz")
def healthz():
    return {"ok": True, "version": __version__}


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"ok": True, "database": "up"}


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(
        APP_DIR / "static" / "manifest.webmanifest",
        media_type="application/manifest+json",
    )


@app.get("/sw.js")
def service_worker():
    return FileResponse(
        APP_DIR / "static" / "sw.js",
        media_type="text/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/media/{kind}/{filename}")
def media(kind: str, filename: str):
    if kind not in {"covers", "photos", "receipts"}:
        raise HTTPException(status_code=404, detail="Not found")
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = safe_join(f"{kind}/{filename}")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response
