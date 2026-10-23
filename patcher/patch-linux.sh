#!/bin/sh
# CHAOS;HEAD NOAH (PSP) English patcher for Linux (also works on macOS / BSD).
# Needs only the Japanese ISO, ChaosHeadNoah_PSP_EN.dat next to this script, and standard tools:
# sh, dd, cp, wc, awk and sha256sum (or shasum). No PC/Steam copy of the game is needed.
# Usage: sh patch-linux.sh "ORIGINAL.iso" ["OUTPUT.iso"]
# The original ISO is never modified; the English ISO is written as a new file.
set -e

DIR=$(cd "$(dirname "$0")" && pwd)
DAT="$DIR/ChaosHeadNoah_PSP_EN.dat"
HEADER=128                  # index sectors at the start of the .dat; data sector 0 follows them

fail() { echo ""; echo "ERROR: $1" >&2; exit 1; }

[ -n "$1" ] || fail "usage: sh patch-linux.sh \"ORIGINAL.iso\" [\"OUTPUT.iso\"]"
ISO=$1
OUT=${2:-"$(dirname "$ISO")/Chaos;Head Noah (English).iso"}
[ -f "$ISO" ] || fail "file not found: $ISO"
[ -f "$DAT" ] || fail "keep this script next to ChaosHeadNoah_PSP_EN.dat"
[ "$ISO" != "$OUT" ] || fail "the output must be a different file from the original ISO"

if command -v sha256sum >/dev/null 2>&1; then
    sha() { sha256sum "$1" | cut -d' ' -f1; }
elif command -v shasum >/dev/null 2>&1; then
    sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
else
    fail "sha256sum not found"
fi

index() { dd if="$DAT" bs=2048 count=$HEADER 2>/dev/null | awk '$1=="end"{exit} {print}'; }
SIZE=$(index | awk '$1=="size"{print $2}')
WANT_SRC=$(index | awk '$1=="source_sha256"{print $2}')
WANT_DST=$(index | awk '$1=="result_sha256"{print $2}')
[ -n "$SIZE" ] || fail "ChaosHeadNoah_PSP_EN.dat is damaged"

echo "Checking the original ISO (this takes a moment)..."
[ "$(wc -c < "$ISO" | tr -d ' ')" = "$SIZE" ] && [ "$(sha "$ISO")" = "$WANT_SRC" ] ||
    fail "this is not the expected ISO: CHAOS;HEAD NOAH (Japan) ULJM05692, unmodified ($SIZE bytes)"

echo "Copying..."
cp "$ISO" "$OUT"

echo "Patching..."
# copy: sectors taken from the original ISO; block: new sectors from the .dat
index | awk -v h=$HEADER '$1=="copy"{print "c", $2, $3, $4} $1=="block"{print "b", $2, $3 + h, $4}' |
while read -r KIND SEEK SKIP COUNT; do
    if [ "$KIND" = c ]; then SRC=$ISO; else SRC=$DAT; fi
    dd if="$SRC" of="$OUT" bs=2048 skip="$SKIP" seek="$SEEK" count="$COUNT" conv=notrunc 2>/dev/null ||
        fail "writing to $OUT failed"
done

echo "Verifying..."
[ "$(sha "$OUT")" = "$WANT_DST" ] || fail "verification failed: delete $OUT and try again"
echo ""
echo "Done: $OUT"
