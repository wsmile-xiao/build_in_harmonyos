#!/bin/sh
# test_swbis.sh — swbis 1.13.3 consumer smoke test.
#
# Standalone shell mirror of test_package/conanfile.py (3 assertions):
#   1. swpackage --version reports 1.13.3
#   2. swlist --version reports 1.13.3
#   3. swpackage packs a tiny payload (tar non-empty + contains catalog)
#
# Usage: sh test_swbis.sh [bindir]
#   bindir defaults to PATH lookup. Exits 0 only if all 3 pass.
set -u

VER="1.13.3"
BINDIR="${1:-}"
if [ -n "$BINDIR" ]; then
    SWPACKAGE="$BINDIR/swpackage"
    SWLIST="$BINDIR/swlist"
else
    SWPACKAGE="swpackage"
    SWLIST="swlist"
fi

pass=0
check() {
    # $1 = description, rest = command
    desc="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        echo "ok: $desc"
        pass=$((pass + 1))
    else
        echo "FAIL: $desc" >&2
        exit 1
    fi
}

check "swpackage --version reports $VER" sh -c "$SWPACKAGE --version 2>&1 | grep -q '$VER'"
check "swlist --version reports $VER" sh -c "$SWLIST --version 2>&1 | grep -q '$VER'"

WORK="$(pwd)/test-work"
rm -rf "$WORK"
mkdir -p "$WORK/payload" || exit 1
echo "hello swbis" > "$WORK/payload/hello.txt" || exit 1
sed "s|@WORK@|$WORK|" "$(dirname "$0")/hellopkg.psf" > "$WORK/hellopkg.work.psf" || exit 1
[ -s "$WORK/hellopkg.work.psf" ] || { echo "FAIL: generated PSF is empty" >&2; exit 1; }
check "swpackage parses PSF (preview)" sh -c "$SWPACKAGE -s '$WORK/hellopkg.work.psf' -p"
check "swpackage builds tar" sh -c "$SWPACKAGE -s '$WORK/hellopkg.work.psf' @ '$WORK/hellopkg.tar'"
check "tar non-empty" test -s "$WORK/hellopkg.tar"
check "tar contains catalog" sh -c "tar -tf '$WORK/hellopkg.tar' | grep -q catalog"

echo "PASS: $pass assertions ($VER)"
