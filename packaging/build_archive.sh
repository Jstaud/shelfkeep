#!/bin/sh
# Package a built shelfkeep binary plus install helper into a .tar.gz.
# Usage: packaging/build_archive.sh <binary> <artifact-stem>
# Writes dist/<artifact-stem>.tar.gz
set -eu

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <binary> <artifact-stem>" >&2
  exit 1
fi

BINARY=$1
STEM=$2
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEST="${ROOT}/dist/${STEM}"
ARCHIVE="${ROOT}/dist/${STEM}.tar.gz"

if [ ! -f "$BINARY" ]; then
  echo "binary not found: $BINARY" >&2
  exit 1
fi

rm -rf "$DEST"
mkdir -p "$DEST"
cp "$BINARY" "$DEST/shelfkeep"
chmod 755 "$DEST/shelfkeep"
cp "$ROOT/packaging/install.sh" "$DEST/install.sh"
chmod 755 "$DEST/install.sh"
cp "$ROOT/packaging/BUNDLE_README.txt" "$DEST/README.txt"
cp "$ROOT/LICENSE" "$DEST/LICENSE"

tar -C "$ROOT/dist" -czf "$ARCHIVE" "$STEM"
echo "$ARCHIVE"
