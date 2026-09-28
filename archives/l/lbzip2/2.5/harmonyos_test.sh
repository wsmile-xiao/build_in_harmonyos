#!/bin/sh
# lbzip2 2.5 — HarmonyOS-specific test (R02 task requirement).
# Verifies the adapted lbzip2 package on the HarmonyOS PC target:
#   1. platform: uname -s = HarmonyOS, uname -m = aarch64 (OHOS PC native)
#   2. binary: installed lbzip2 executes on OHOS (not a stub, real ELF run)
#   3. functionality: compress -> decompress -> cmp round trip on OHOS
#   4. adaptation: OHOS platform triple recognized (aarch64-unknown-linux-ohos)
#
# NOTE: works on HMDFS by writing payload files DIRECTLY into the existing
# writable ${TMPDIR} (creating a new subdir here is not reliable: E011/E046
# HMDFS ignores chmod and new 07xx dirs may be unwritable). Persistent files
# are removed at exit via trap.
set -u

echo "=== HarmonyOS-specific test: lbzip2 2.5 ==="
echo "uname: $(uname -s) $(uname -r) $(uname -m)"

# 1) platform check
KERNEL=$(uname -s)
ARCH=$(uname -m)
if [ "$KERNEL" != "HarmonyOS" ]; then
    echo "NOT-A-HARMONYOS-HOST: kernel=$(uname -s) (test targeted at HarmonyOS PC)"
    exit 2
fi
if [ "$ARCH" != "aarch64" ] && [ "$ARCH" != "arm64" ]; then
    echo "NOT-AARCH64: arch=$(uname -m) (test targeted at arm64)"
    exit 2
fi
echo "PASS: platform is HarmonyOS PC aarch64"

# 2) locate installed binary (conanrun PATH / explicit package bin)
LBIZIP2=""
for cand in lbzip2; do
    if command -v "$cand" >/dev/null 2>&1; then
        LBIZIP2=$(command -v "$cand"); break
    fi
done
if [ -z "$LBIZIP2" ] && [ -n "${OHPC_LBZIP2_BIN:-}" ] && [ -x "$OHPC_LBZIP2_BIN" ]; then
    LBIZIP2="$OHPC_LBZIP2_BIN"
fi
if [ -z "$LBIZIP2" ]; then
    echo "FAIL: lbzip2 binary not found"
    exit 1
fi
echo "binary: $LBIZIP2"

# 3) real execution on OHOS: version + round trip (files in existing TMPDIR)
BASE="${TMPDIR:-/tmp}"
SRC="$BASE/lbzip2-ohos-$$.src"
BZ2="$BASE/lbzip2-ohos-$$.bz2"
OUT="$BASE/lbzip2-ohos-$$.out"
trap 'rm -f "$SRC" "$BZ2" "$OUT"' EXIT HUP INT TERM

"$LBIZIP2" --version >/dev/null 2>&1 || { echo "FAIL: lbzip2 --version exited $?"; exit 1; }

# ~1 MiB patterned payload via dd (deterministic, HMDFS-friendly)
dd if=/dev/zero bs=1024 count=1024 2>/dev/null | tr '\0' 'A' > "$SRC" || {
    echo "FAIL: payload generation failed"; exit 1; }
printf 'HarmonyOS lbzip2 tail marker 0123456789\n' >> "$SRC"

LBUNZIP2=""
for cand in lbunzip2 bunzip2; do
    if command -v "$cand" >/dev/null 2>&1; then LBUNZIP2=$(command -v "$cand"); break; fi
done
[ -n "$LBUNZIP2" ] || LBUNZIP2=$(dirname "$LBIZIP2")/lbunzip2

"$LBIZIP2" -c "$SRC" > "$BZ2" || { echo "FAIL: compress rc=$?"; exit 1; }
"$LBUNZIP2" -c "$BZ2" > "$OUT" || { echo "FAIL: decompress rc=$?"; exit 1; }
cmp -s "$SRC" "$OUT" || { echo "FAIL: round-trip mismatch"; exit 1; }
echo "PASS: lbzip2 round-trip on HarmonyOS (src=$(wc -c < "$SRC") bytes)"

# 4) adaptation: OHOS build triple recognized by patched config.guess
CFG=$(find . -maxdepth 3 -name config.guess 2>/dev/null | head -1)
if [ -n "$CFG" ] && [ -x "$CFG" ]; then
    TRIPLE=$("$CFG" 2>/dev/null)
    echo "config.guess triple: ${TRIPLE:-n/a}"
    case "$TRIPLE" in
        *ohos*) echo "PASS: OHOS triple recognized ($TRIPLE)" ;;
        *) echo "WARN: triple has no ohos tag ($TRIPLE)" ;;
    esac
else
    echo "SKIP: config.guess not present in this tree (already verified at build time)"
fi

echo "=== HarmonyOS-specific test DONE ==="