# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Shelfkeep binary (Linux + macOS)."""

from pathlib import Path

spec_dir = Path(SPECPATH)
root = spec_dir.parent

a = Analysis(
    [str(root / "app" / "cli.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "app" / "templates"), "app/templates"),
        (str(root / "app" / "static"), "app/static"),
    ],
    hiddenimports=[
        "app",
        "app.cli",
        "app.main",
        "app.auth",
        "app.config",
        "app.db",
        "app.metadata",
        "app.models",
        "app.routers",
        "app.routers.api",
        "app.routers.pages",
        "app.schemas",
        "app.serializers",
        "app.uploads",
        "multipart",
        "PIL",
        "psycopg",
        "psycopg_binary",
        "pydantic_settings",
        "sqlalchemy.dialects.postgresql",
        "sqlalchemy.dialects.sqlite",
        "uvicorn.lifespan",
        "uvicorn.lifespan.off",
        "uvicorn.lifespan.on",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.loops.uvloop",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.protocols.websockets.wsproto_impl",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="shelfkeep",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
