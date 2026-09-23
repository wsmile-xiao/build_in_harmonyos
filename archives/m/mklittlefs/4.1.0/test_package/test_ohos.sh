#!/usr/bin/env bash
# test_package/test_ohos.sh — OHOS-specific tests for mklittlefs 4.1.0
#
# Verifies the built binary is a proper OHOS executable and that
# create/list/extract work under the OpenHarmony PC environment
# (HMDFS-backed home directory semantics).
#
# Assertions (no skips allowed — any failure exits non-zero):
#   1. ELF64 AArch64
#   2. PT_INTERP == /lib/ld-musl-aarch64.so.1
#   3. .codesign section present
#   4. No host RPATH/RUNPATH and no absolute host paths in NEEDED
#   5. Real create/list/extract under HMDFS home dir (byte-exact)
#   6. Unpacked file permissions and paths
#
# No network, no pre-built binary fixtures.
set -euo pipefail

BIN=$(command -v mklittlefs) || { echo "FAIL: mklittlefs not on PATH" >&2; exit 1; }

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

echo "[1/6] ELF64 AArch64"
readelf -h "$BIN" | grep -q "Class:.*ELF64" || fail "not ELF64"
readelf -h "$BIN" | grep -q "Machine:.*AArch64" || fail "not AArch64"

echo "[2/6] PT_INTERP is musl aarch64 loader"
readelf -l "$BIN" | grep -A2 INTERP | grep -q "/lib/ld-musl-aarch64.so.1" || fail "bad PT_INTERP"

echo "[3/6] .codesign section present"
readelf -S "$BIN" | grep -q "\.codesign" || fail "no .codesign section"

echo "[4/6] no host RPATH/RUNPATH, no absolute host paths"
if readelf -d "$BIN" | grep -qE "RPATH|RUNPATH"; then
    readelf -d "$BIN" | grep -E "RPATH|RUNPATH"
    fail "host RPATH/RUNPATH found"
fi
if readelf -d "$BIN" | grep -E "NEEDED" | grep -qE "/(storage|home|Users)/"; then
    fail "absolute host path in NEEDED"
fi

echo "[5/6] create/list/extract round-trip under HMDFS home dir"
# Use home directory: /tmp is read-only on this OHOS PC and mktemp -d
# under /tmp would fail. HMDFS home is the canonical writable location.
WORK=$(mktemp -d "$HOME/mklfs.ohos.XXXXXX") || fail "mktemp in HOME failed"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/in/nested/deep"
printf 'ohos hmdfs test\n' > "$WORK/in/nested/deep/file.txt"
printf '\000\001\002bin\000' > "$WORK/in/nested/blob.bin"
SIZE=1048576
IMG="$WORK/test.img"

mklittlefs -c "$WORK/in" -s "${SIZE}" "$IMG" || fail "create failed"
LIST=$(mklittlefs -l "$IMG") || fail "list failed"
# nested paths print with upstream's concatenated form
echo "$LIST" | grep -qF '//nested/deepfile.txt' || fail "list missing nested/deep/file.txt"
echo "$LIST" | grep -qF '//nestedblob.bin' || fail "list missing nested/blob.bin"

mkdir -p "$WORK/out"
mklittlefs -u "$WORK/out" -s "${SIZE}" "$IMG" || fail "extract failed"

[ -f "$WORK/out/nested/deep/file.txt" ] || fail "extracted file.txt missing"
[ -f "$WORK/out/nested/blob.bin" ] || fail "extracted blob.bin missing"
cmp "$WORK/in/nested/deep/file.txt" "$WORK/out/nested/deep/file.txt" \
    || fail "file.txt bytes differ"
cmp "$WORK/in/nested/blob.bin" "$WORK/out/nested/blob.bin" \
    || fail "blob.bin bytes differ"

echo "[6/6] extracted file permissions and paths"
for f in nested/deep/file.txt nested/blob.bin; do
    [ -f "$WORK/out/$f" ] || fail "path missing: $f"
    # regular readable file (HMDFS yields 0660-ish for new files; only
    # assert readable, not exact mode bits)
    [ -r "$WORK/out/$f" ] || fail "not readable: $f"
done

echo "mklittlefs test_ohos: OK"
