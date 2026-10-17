#!/bin/bash
# 打包布局与纯度校验 for ino-headers 0.4.0 (R34).
# Usage: check_pkg.sh <package_folder>
# Exits non-zero on the first violation.

PKG_DIR="$1"
[ -n "$PKG_DIR" ] || { echo "FAIL: package_folder arg missing"; exit 1; }

fail() { echo "FAIL: $*"; exit 1; }
pass() { echo "PASS: $*"; }

HEADER="$PKG_DIR/include/ino-0/ino/lib.h"
PCFILE="$PKG_DIR/lib/pkgconfig/ino-headers-0.pc"

# --- 1. header layout (upstream: ${includedir}/ino-0/ino/lib.h) ---
[ -s "$HEADER" ] || fail "header missing or empty: $HEADER"
grep -q "ino_context_new" "$HEADER" || fail "lib.h does not declare ino_context_new"
pass "include/ino-0/ino/lib.h present with public API ($(wc -l < "$HEADER") lines)"

# --- 2. pkgconfig relocatability ---
[ -f "$PCFILE" ] || fail "pkgconfig file missing: $PCFILE"
grep -q "^Version: 0.4.0" "$PCFILE" || fail "pc file Version is not 0.4.0"
grep -q -- "-I\${includedir}/ino-0" "$PCFILE" \
    || fail "pc Cflags does not declare -I\${includedir}/ino-0"
if grep -qE "^(prefix|exec_prefix|includedir)=/" "$PCFILE"; then
    fail "pc file contains absolute paths (not relocatable)"
fi
pass "ino-headers-0.pc installed; Version + Cflags + relocatable prefix verified"

# --- 3. purity: header-only package (R38) ---
[ ! -d "$PKG_DIR/bin" ] || fail "unexpected bin/ directory in header-only package"
ARTIFACTS=$(find "$PKG_DIR/lib" -type f ! -path "*/pkgconfig/*" 2>/dev/null | wc -l)
[ "$ARTIFACTS" -eq 0 ] \
    || fail "$ARTIFACTS non-pkgconfig file(s) under lib/ in header-only package"
pass "no bin/ artifacts, no compiled libs (header-only package confirmed)"

echo "ALL CHECKS PASSED: ino-headers package layout verification (R34 substantive)"
exit 0
