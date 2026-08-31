from pathlib import Path
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    session_secret: str = "change-this-session-secret"
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
    def using_default_secrets(self) -> bool:
        return (
            self.shelfkeep_password == "changeme"
            or self.session_secret
            in {"change-this-session-secret", "replace-with-a-long-random-string"}
        )


settings = Settings()
