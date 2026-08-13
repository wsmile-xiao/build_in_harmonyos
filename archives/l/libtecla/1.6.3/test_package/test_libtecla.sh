#!/bin/sh
# test_libtecla.sh — L1 test for libtecla 1.6.3
# Verifies the packaged static library:
#   1. include/libtecla.h and lib/libtecla.a exist
#   2. a C program linking the packaged header + static lib compiles and
#      runs, with libtecla_version() reporting 1.6.3 (R34 substantive)
# set -e is intentionally omitted: PASS/FAIL counting relies on non-zero
# exits from failed assertions to continue and summarize.
set -u
set -o pipefail

PASS=0
FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
no() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# Locate the libtecla package root.
# Priority 1: LIBTECLA_PKG_ROOT env var (from test_package conanfile.py).
# Priority 2: search the Conan cache for the packaged header.
PKG_ROOT=""
if [ -n "${LIBTECLA_PKG_ROOT:-}" ] && [ -f "${LIBTECLA_PKG_ROOT}/include/libtecla.h" ]; then
    PKG_ROOT="${LIBTECLA_PKG_ROOT}"
fi
if [ -z "$PKG_ROOT" ]; then
    FOUND=$(find "$HOME/.conan2/p" -path "*/include/libtecla.h" -type f 2>/dev/null | head -1)
    if [ -n "$FOUND" ]; then
        PKG_ROOT=$(echo "$FOUND" | sed 's|/include/libtecla.h$||')
    fi
fi

echo "=== libtecla L1 test ==="
echo "  package root: ${PKG_ROOT:-<not found>}"

if [ -z "$PKG_ROOT" ]; then
    no "package root not found"
    echo ""
    echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
    exit 1
fi

# 1) artifacts exist
if [ -f "$PKG_ROOT/include/libtecla.h" ]; then
    ok "include/libtecla.h exists"
else
    no "include/libtecla.h missing"
fi
if [ -f "$PKG_ROOT/lib/libtecla.a" ]; then
    ok "lib/libtecla.a exists"
else
    no "lib/libtecla.a missing"
fi

# 2) compile + run a C program against the packaged header + static lib
WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/libtecla-test.XXXXXX" 2>/dev/null || mktemp -d 2>/dev/null)
if [ -z "$WORKDIR" ]; then
    WORKDIR="$HOME/tmp/libtecla-test"
    mkdir -p "$WORKDIR"
fi
cat > "$WORKDIR/test_libtecla.c" <<'EOF'
#include <libtecla.h>
#include <stdio.h>
int main(void) {
  int major = 0, minor = 0, micro = 0;
  libtecla_version(&major, &minor, &micro);
  printf("libtecla %d.%d.%d\n", major, minor, micro);
  return (major == 1 && minor == 6 && micro == 3) ? 0 : 1;
}
EOF
# Use the toolchain C compiler passed by test_package/conanfile.py (CC),
# falling back to gcc for local runs; gcc does not exist on OHOS.
CC="${CC:-gcc}"
if "$CC" -I"$PKG_ROOT/include" "$WORKDIR/test_libtecla.c" "$PKG_ROOT/lib/libtecla.a" \
       -o "$WORKDIR/test_libtecla" 2>"$WORKDIR/cc.err"; then
    OUT=$("$WORKDIR/test_libtecla" 2>&1)
    RC=$?
    if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q "1.6.3"; then
        ok "linked + ran: $OUT"
    else
        no "test program failed (rc=$RC): $OUT"
    fi
else
    no "compile failed: $(head -2 "$WORKDIR/cc.err")"
fi
rm -rf "$WORKDIR"

echo ""
echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
