#!/bin/bash
# Substantive data-package verification for mypaint-brushes 2.0.2.1 (R34).
# Usage: test_mypaint_brushes.sh <package_folder>
# Exits non-zero on the first integrity violation.

PKG_DIR="$1"
[ -n "$PKG_DIR" ] || { echo "FAIL: package_folder arg missing"; exit 1; }

fail() { echo "FAIL: $*"; exit 1; }
pass() { echo "PASS: $*"; }

BRUSHES="$PKG_DIR/share/mypaint-data/2.0/brushes"
PCFILE="$PKG_DIR/share/pkgconfig/mypaint-brushes-2.0.pc"

# --- 1. packaged layout ---
[ -d "$BRUSHES" ] || fail "brushes dir missing: $BRUSHES"
pass "brushes dir present: $BRUSHES"

for g in Dieterle classic deevad experimental kaerhon_v1 ramon tanda; do
    [ -d "$BRUSHES/$g" ] || fail "brush group dir missing: $g"
done
pass "all 7 upstream brush groups present (Dieterle/classic/deevad/experimental/kaerhon_v1/ramon/tanda)"

# --- 2. order.conf <-> disk cross-check ---
[ -s "$BRUSHES/order.conf" ] || fail "order.conf missing or empty"
LINES=$(wc -l < "$BRUSHES/order.conf")
ENTRIES=$(grep -vE '^[[:space:]]*(#|$|Group:)' "$BRUSHES/order.conf" | grep -c .)
[ "$ENTRIES" -ge 190 ] || fail "order.conf has only $ENTRIES brush entries (expected >=190)"
MISSING=0
while IFS= read -r entry; do
    [ -n "$entry" ] || continue
    [ -f "$BRUSHES/$entry.myb" ] || {
        MISSING=$((MISSING + 1))
        [ "$MISSING" -le 5 ] && echo "  missing .myb for order.conf entry: $entry"
    }
done < <(grep -vE '^[[:space:]]*(#|$|Group:)' "$BRUSHES/order.conf")
[ "$MISSING" -eq 0 ] || fail "$MISSING/$ENTRIES order.conf entries have no .myb on disk"
pass "order.conf <-> disk cross-check: $ENTRIES/$ENTRIES entries resolve to real .myb files ($LINES lines)"

# --- 3. brush file content sanity ---
MYB_COUNT=$(find "$BRUSHES" -name '*.myb' -type f | wc -l)
[ "$MYB_COUNT" -ge 190 ] || fail "expected >=190 .myb files, got $MYB_COUNT"
pass "found $MYB_COUNT .myb brush files"
SAMPLE=$(find "$BRUSHES" -name '*.myb' -type f | head -1)
if command -v od >/dev/null 2>&1; then
    MAGIC=$(od -An -tx1 -N2 "$SAMPLE" | tr -d ' \n')
    # MyPaint 2.x brush files are either gzipped JSON (1f8b) or plain JSON
    # objects (0x7b '{'). This 2.0.2 tarball ships plain-JSON .myb files
    # (verified: 196/196 files start with 7b). Accept both valid formats.
    case "$MAGIC" in
        1f8b|7b*) pass "sample .myb header valid ($MAGIC: gzip/JSON brush format): $(basename "$SAMPLE")" ;;
        *) fail "sample .myb has unexpected magic ($MAGIC): $SAMPLE" ;;
    esac
else
    SIZE=$(wc -c < "$SAMPLE")
    [ "$SIZE" -gt 100 ] || fail "sample .myb suspiciously small ($SIZE bytes)"
    pass "od unavailable; sample .myb size sanity OK ($SIZE bytes)"
fi

# --- 4. pkgconfig declaration ---
[ -f "$PCFILE" ] || fail "pkgconfig file missing: $PCFILE"
grep -q "mypaint-data/2.0/brushes" "$PCFILE" || fail "pc file does not declare the installed brushesdir"
grep -q "^Version: 2.0.2" "$PCFILE" || fail "pc file Version is not 2.0.2"
pass "mypaint-brushes-2.0.pc installed; brushesdir + Version=2.0.2 verified"

# --- 5. purity: data-only package (R38) ---
[ ! -d "$PKG_DIR/lib" ] || fail "unexpected lib/ directory in pure data package"
[ ! -d "$PKG_DIR/bin" ] || fail "unexpected bin/ directory in pure data package"
pass "no lib/ or bin/ artifacts (pure data package confirmed)"

echo "ALL CHECKS PASSED: mypaint-brushes data package verification (R34 substantive)"
exit 0
