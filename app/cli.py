"""Command-line entry for packaged and source installs.

``shelfkeep`` and ``shelfkeep serve`` start the web UI. The binary defaults
to 127.0.0.1:8080, SQLite, and a user-writable DATA_DIR. Compose / Docker
still launch uvicorn directly on 0.0.0.0:8080.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from app import __version__


def default_host() -> str:
    return os.environ.get("SHELFKEEP_HOST", "127.0.0.1")


def default_port() -> int:
    raw = os.environ.get("SHELFKEEP_PORT", "8080")
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(f"SHELFKEEP_PORT must be an integer, got {raw!r}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shelfkeep",
        description="Shelfkeep — self-hosted catalog and home inventory.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Shelfkeep {__version__}",
    )

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--host",
        default=default_host(),
        help="Bind address (default 127.0.0.1; SHELFKEEP_HOST). "
        "Use 0.0.0.0 to listen on all interfaces.",
    )
    common.add_argument(
        "--port",
        type=int,
        default=default_port(),
        help="Bind port (default 8080; SHELFKEEP_PORT).",
    )

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("serve", parents=[common], help="Start the web UI (default).")
    sub.add_parser("version", help="Print the application version and exit.")

    # ``shelfkeep --host/--port`` without a subcommand also serves.
    parser.add_argument("--host", default=default_host(), help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=default_port(), help=argparse.SUPPRESS)
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(list(argv) if argv is not None else None)


def serve(host: str, port: int) -> int:
    import uvicorn

    from app.config import settings
    from app.main import app

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    print(f"Shelfkeep {__version__}  http://{host}:{port}", flush=True)
    print(f"Data directory: {settings.data_dir.resolve()}", flush=True)
    print("Ctrl+C to stop.", flush=True)
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "version":
        print(__version__)
        return 0
    return serve(args.host, args.port)


if __name__ == "__main__":
    raise SystemExit(main())
