#!/bin/sh
# CHAOS;HEAD NOAH (PSP) English patcher for Linux (also works on macOS / BSD).
# Needs only standard tools: sh, dd, cp, wc and sha256sum (or shasum).
# Usage: sh patch-linux.sh "ORIGINAL.iso" ["OUTPUT.iso"]
# The original ISO is never modified; the English ISO is written as a new file.
set -e

DIR=$(cd "$(dirname "$0")" && pwd)
IDX="$DIR/ChaosHeadNoah_PSP_EN.patch.txt"
BIN="$DIR/ChaosHeadNoah_PSP_EN.patch.bin"

fail() { echo ""; echo "ERROR: $1" >&2; exit 1; }

[ -n "$1" ] || fail "usage: sh patch-linux.sh \"ORIGINAL.iso\" [\"OUTPUT.iso\"]"
ISO=$1
OUT=${2:-"$(dirname "$ISO")/Chaos;Head Noah (English).iso"}
[ -f "$ISO" ] || fail "file not found: $ISO"
[ -f "$IDX" ] && [ -f "$BIN" ] || fail "keep this script next to ChaosHeadNoah_PSP_EN.patch.txt and .patch.bin"
[ "$ISO" != "$OUT" ] || fail "the output must be a different file from the original ISO"

if command -v sha256sum >/dev/null 2>&1; then
    sha() { sha256sum "$1" | cut -d' ' -f1; }
elif command -v shasum >/dev/null 2>&1; then
    sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
else
    fail "sha256sum not found"
fi

SIZE=$(awk '$1=="size"{print $2}' "$IDX")
WANT_SRC=$(awk '$1=="source_sha256"{print $2}' "$IDX")
WANT_DST=$(awk '$1=="result_sha256"{print $2}' "$IDX")

echo "Checking the original ISO (this takes a moment)..."
[ "$(wc -c < "$ISO" | tr -d ' ')" = "$SIZE" ] && [ "$(sha "$ISO")" = "$WANT_SRC" ] ||
    fail "this is not the expected ISO: CHAOS;HEAD NOAH (Japan) ULJM05692, unmodified ($SIZE bytes)"

echo "Copying..."
cp "$ISO" "$OUT"

echo "Patching..."
# copy: sectors taken from the original ISO; block: new sectors from the .bin
awk '$1=="copy" || $1=="block"{print $1, $2, $3, $4}' "$IDX" | while read -r KIND SEEK SKIP COUNT; do
    if [ "$KIND" = copy ]; then SRC=$ISO; else SRC=$BIN; fi
    dd if="$SRC" of="$OUT" bs=2048 skip="$SKIP" seek="$SEEK" count="$COUNT" conv=notrunc 2>/dev/null ||
        fail "writing to $OUT failed"
done

echo "Verifying..."
[ "$(sha "$OUT")" = "$WANT_DST" ] || fail "verification failed: delete $OUT and try again"
echo ""
echo "Done: $OUT"
