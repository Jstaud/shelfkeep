import secrets
from pathlib import Path
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict

# Documented placeholders that must never sign cookies in a running instance.
INSECURE_SESSION_SECRETS = frozenset(
    {
        "",
        "change-this-session-secret",
        "replace-with-a-long-random-string",
    }
)
SESSION_SECRET_FILENAME = ".session_secret"


def postgres_database_url(
    *,
    user: str,
    password: str,
    host: str,
    database: str,
    port: int = 5432,
) -> str:
    """Build a SQLAlchemy URL with credentials encoded for reserved characters."""
    return (
        f"postgresql+psycopg://{quote(user, safe='')}:{quote(password, safe='')}"
        f"@{host}:{port}/{quote(database, safe='')}"
    )


def is_insecure_session_secret(value: str | None) -> bool:
    return (value or "").strip() in INSECURE_SESSION_SECRETS


def resolve_session_secret(configured: str | None, data_dir: Path) -> str:
    """Use a provided secret, or generate and persist one under data_dir.

    Public placeholders from .env.example / Compose defaults must not sign
    shelfkeep_session — anyone who can reach /login could otherwise forge it.
    """
    candidate = (configured or "").strip()
    if not is_insecure_session_secret(candidate):
        return candidate

    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / SESSION_SECRET_FILENAME
    if path.is_file():
        stored = path.read_text(encoding="utf-8").strip()
        if stored:
            return stored

    generated = secrets.token_urlsafe(48)
    try:
        path.write_text(generated, encoding="utf-8")
        path.chmod(0o600)
    except OSError as exc:
        raise RuntimeError(
            "SESSION_SECRET is missing or is a publicly known placeholder. "
            "Set a unique SESSION_SECRET, or make DATA_DIR writable so one "
            "can be generated and persisted."
        ) from exc
    return generated


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite+pysqlite:///./data/shelfkeep.db"
    postgres_host: str | None = None
    postgres_port: int = 5432
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_db: str | None = None
    shelfkeep_username: str = "admin"
    shelfkeep_password: str = "changeme"
    session_secret: str = ""
    data_dir: Path = Path("./data")
    session_https_only: bool = False

    @property
    def resolved_database_url(self) -> str:
        if self.postgres_host:
            return postgres_database_url(
                user=self.postgres_user or "shelfkeep",
                password=self.postgres_password or "",
                host=self.postgres_host,
                database=self.postgres_db or "shelfkeep",
                port=self.postgres_port,
            )
        return self.database_url

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def is_sqlite(self) -> bool:
        return self.resolved_database_url.startswith("sqlite")

    @property
    def resolved_session_secret(self) -> str:
        return resolve_session_secret(self.session_secret, self.data_dir)

    @property
    def using_default_secrets(self) -> bool:
        return self.shelfkeep_password == "changeme"


settings = Settings()
