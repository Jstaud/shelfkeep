from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite+pysqlite:///./data/shelfkeep.db"
    shelfkeep_username: str = "admin"
    shelfkeep_password: str = "changeme"
    session_secret: str = "change-this-session-secret"
    data_dir: Path = Path("./data")
    session_https_only: bool = False

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def using_default_secrets(self) -> bool:
        return (
            self.shelfkeep_password == "changeme"
            or self.session_secret
            in {"change-this-session-secret", "replace-with-a-long-random-string"}
        )


settings = Settings()
