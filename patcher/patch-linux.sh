#!/bin/sh
# CHAOS;HEAD NOAH (PSP) English patcher for Linux (also works on macOS / BSD).
# Needs only the Japanese ISO, ChaosHeadNoah_PSP_EN.dat next to this script, and standard tools:
# sh, dd, cp, wc, head, awk and sha256sum (or shasum). No PC/Steam copy of the game is needed.
# Usage: sh patch-linux.sh "ORIGINAL.iso" ["OUTPUT.iso"]
# The original ISO is never modified; the English ISO is written as a new file.
set -e

DIR=$(cd "$(dirname "$0")" && pwd)
DAT="$DIR/ChaosHeadNoah_PSP_EN.dat"
HEADER=128                  # index sectors at the start of the .dat; data sector 0 follows them

fail() { echo ""; echo "ERROR: $1" >&2; exit 1; }

[ -n "$1" ] || fail "usage: sh patch-linux.sh \"ORIGINAL.iso\" [\"OUTPUT.iso\"]"
ISO=$1
if [ -n "$2" ]; then OUT=$2; else
    # never overwrite: an existing English ISO gets a numbered sibling instead
    OUT="$(dirname "$ISO")/Chaos;Head Noah (English).iso"; N=2
    while [ -e "$OUT" ] || [ "$OUT" = "$ISO" ]; do OUT="$(dirname "$ISO")/Chaos;Head Noah (English) ($N).iso"; N=$((N+1)); done
fi
[ -f "$ISO" ] || fail "file not found: $ISO"
[ -f "$DAT" ] || fail "keep this script next to ChaosHeadNoah_PSP_EN.dat"
[ "$ISO" != "$OUT" ] || fail "the output must be a different file from the original ISO"

if command -v sha256sum >/dev/null 2>&1; then
    sha() { sha256sum | cut -d' ' -f1; }
elif command -v shasum >/dev/null 2>&1; then
    sha() { shasum -a 256 | cut -d' ' -f1; }
else
    fail "sha256sum not found"
fi

index() { dd if="$DAT" bs=2048 count=$HEADER 2>/dev/null | awk '$1=="end"{exit} {print}'; }
SIZE=$(index | awk '$1=="size"{print $2}')
[ -n "$SIZE" ] || fail "ChaosHeadNoah_PSP_EN.dat is damaged"

echo "Checking the original ISO (this takes a moment)..."
[ "$(wc -c < "$ISO" | tr -d ' ')" = "$SIZE" ] ||
    fail "this is not the expected ISO: CHAOS;HEAD NOAH (Japan) ULJM05692, unmodified ($SIZE bytes)"
SRC_SHA=$(sha < "$ISO")
DONE=$(index | awk -v h="$SRC_SHA" '$1=="patched" && $2==h {print $3}')
[ -z "$DONE" ] || fail "this ISO is already the English patch (version $DONE); patch your original Japanese ISO instead"
# the main dump (source/result) and other accepted dumps such as the PSN release (variant lines)
WANT_DST=$(index | awk -v h="$SRC_SHA" '$1=="source_sha256"{s=$2} $1=="result_sha256"{r=$2} $1=="variant" && $2==h {v=$3}
                                       END {if (s==h) print r; else if (v!="") print v}')
[ -n "$WANT_DST" ] ||
    fail "this is not the expected ISO: CHAOS;HEAD NOAH (Japan) ULJM05692, unmodified ($SIZE bytes)"

echo "Copying..."
cp "$ISO" "$OUT" || fail "cannot write $OUT (is it open in another program?)"

echo "Patching..."
# copy: sectors taken from the original ISO; block: new sectors from the .dat
index | awk -v h=$HEADER '$1=="copy"{print "c", $2, $3, $4} $1=="block"{print "b", $2, $3 + h, $4}' |
while read -r KIND SEEK SKIP COUNT; do
    if [ "$KIND" = c ]; then SRC=$ISO; else SRC=$DAT; fi
    dd if="$SRC" of="$OUT" bs=2048 skip="$SKIP" seek="$SEEK" count="$COUNT" conv=notrunc 2>/dev/null ||
        fail "writing to $OUT failed"
done

echo "Checking every patched file..."
# file lines: expected sha256, first sector, size, path of each file the patch wrote
CHECK=$(index | awk '$1=="file"')
BAD=0; FILES=0
while read -r _ WANT LBA BYTES NAME; do
    GOT=$(dd if="$OUT" bs=2048 skip="$LBA" count=$(( (BYTES + 2047) / 2048 )) 2>/dev/null | head -c "$BYTES" | sha)
    FILES=$((FILES + 1))
    if [ "$GOT" = "$WANT" ]; then echo "  [OK]   $NAME ($BYTES bytes)"; else echo "  [FAIL] $NAME ($BYTES bytes)"; BAD=$((BAD + 1)); fi
done <<EOF
$CHECK
EOF
[ "$BAD" = 0 ] || fail "$BAD file(s) failed the check: delete $OUT and try again"
echo "Checking the whole ISO..."
OUT_SHA=$(sha < "$OUT")
[ "$OUT_SHA" = "$WANT_DST" ] || fail "verification failed: delete $OUT and try again"
echo ""
echo "Check passed: 100% patched."
echo "  $FILES of $FILES patched files verified, each in its correct place"
echo "  every byte ($(wc -c < "$OUT" | tr -d ' ')) of the ISO matches the expected English ISO"
echo "  SHA-256 $OUT_SHA"
echo ""
echo "Done: $OUT"
