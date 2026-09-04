#!/bin/sh
# Install the Shelfkeep binary into ~/.local/bin (override with PREFIX/BINDIR).
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PREFIX="${PREFIX:-$HOME/.local}"
BINDIR="${BINDIR:-$PREFIX/bin}"
SOURCE="$SCRIPT_DIR/shelfkeep"

if [ ! -f "$SOURCE" ]; then
  echo "install.sh: shelfkeep binary not found next to this script" >&2
  exit 1
fi

mkdir -p "$BINDIR"
if command -v install >/dev/null 2>&1; then
  install -m 755 "$SOURCE" "$BINDIR/shelfkeep"
else
  cp "$SOURCE" "$BINDIR/shelfkeep"
  chmod 755 "$BINDIR/shelfkeep"
fi

echo "Installed $BINDIR/shelfkeep"
case ":${PATH}:" in
  *":${BINDIR}:"*) ;;
  *)
    echo "Add ${BINDIR} to PATH, for example:"
    echo "  export PATH=\"${BINDIR}:\$PATH\""
    ;;
esac
echo "Then run:  shelfkeep"
echo "Open http://127.0.0.1:8080  (default login admin / changeme — change SHELFKEEP_PASSWORD)"
