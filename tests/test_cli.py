import sys
from pathlib import Path

import pytest

from app import __version__
from app.cli import main, parse_args
from app.config import (
    DEFAULT_SQLITE_URL,
    Settings,
    default_data_dir,
    sqlite_url_for,
    user_data_dir,
)


def test_cli_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "serve" in out
    assert "self-hosted" in out.lower()


def test_cli_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_cli_version_subcommand(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


def test_parse_args_defaults_to_localhost():
    args = parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 8080
    assert args.command is None


def test_parse_args_serve_overrides():
    args = parse_args(["serve", "--host", "0.0.0.0", "--port", "9090"])
    assert args.command == "serve"
    assert args.host == "0.0.0.0"
    assert args.port == 9090


def test_parse_args_reads_host_port_env(monkeypatch):
    monkeypatch.setenv("SHELFKEEP_HOST", "0.0.0.0")
    monkeypatch.setenv("SHELFKEEP_PORT", "9090")
    args = parse_args([])
    assert args.host == "0.0.0.0"
    assert args.port == 9090


def test_default_data_dir_is_local_in_source_tree():
    assert default_data_dir() == Path("./data")


def test_default_data_dir_frozen_uses_user_path(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.is_frozen", lambda: True)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert default_data_dir() == tmp_path / "shelfkeep"


def test_user_data_dir_linux_xdg(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert user_data_dir() == tmp_path / "shelfkeep"


def test_user_data_dir_darwin(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr("app.config.Path.home", staticmethod(lambda: tmp_path))
    assert user_data_dir() == tmp_path / "Library" / "Application Support" / "shelfkeep"


def test_default_sqlite_follows_data_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(data_dir=tmp_path)
    assert "database_url" not in settings.model_fields_set
    assert settings.resolved_database_url == sqlite_url_for(tmp_path)
    assert str(tmp_path / "shelfkeep.db") in settings.resolved_database_url


def test_explicit_database_url_wins(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(
        data_dir=tmp_path,
        database_url="sqlite+pysqlite:////tmp/custom.db",
    )
    assert settings.resolved_database_url == "sqlite+pysqlite:////tmp/custom.db"


def test_explicit_default_sqlite_url_is_not_rewritten(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(data_dir=tmp_path, database_url=DEFAULT_SQLITE_URL)
    assert "database_url" in settings.model_fields_set
    assert settings.resolved_database_url == DEFAULT_SQLITE_URL


def test_postgres_host_still_wins_over_sqlite_default(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(
        postgres_host="db",
        postgres_user="shelfkeep",
        postgres_password="secret",
        postgres_db="shelfkeep",
    )
    assert settings.resolved_database_url.startswith("postgresql+psycopg://")
    assert "@db:5432/shelfkeep" in settings.resolved_database_url


def test_compose_keeps_local_build_and_optional_image():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "build: ." in compose
    assert "SHELFKEEP_IMAGE" in compose
    assert "ghcr.io/jstaud/shelfkeep" in compose
    assert "kind: Deployment" not in compose


def test_readme_docker_run_binds_localhost():
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "-p 127.0.0.1:8080:8080" in readme
    standalone = readme.split("Standalone `docker run`")[1].split("### 3.")[0]
    assert "-p 8080:8080" not in standalone
    assert "SHELFKEEP_PASSWORD='your-password-here'" in standalone
    assert "-p 127.0.0.1:8080:8080" in standalone
    assert "does **not** run on Intel Macs" in readme
    assert "`macos-15`" in readme
    assert "arm64-only" in readme
