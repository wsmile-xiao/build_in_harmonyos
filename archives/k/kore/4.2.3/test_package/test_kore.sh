#!/usr/bin/env bash
set -euo pipefail
# test_package/test_kore.sh — kore 4.2.3 consumer smoke test (5 assertions).
#
# R34: executes the packaged kore/kodev binaries and checks the installed
# layout. Called by test_package/conanfile.py test().
# Any failed assertion exits 1 with a diagnostic message.

KORE_BIN="${1:-kore}"
KODEV_BIN="${2:-kodev}"
PKG_DIR="${3:-.}"

if [ ! -x "$KORE_BIN" ]; then
    echo "FAIL(1/5): kore binary not executable at $KORE_BIN" >&2
    ls -la "$KORE_BIN" >&2 || true
    exit 1
fi
echo "PASS(1/5): kore binary exists and is executable"

# Assertion 2: kore -v exits 0 and reports the packaged version.
version_rc=0
version_out=$("$KORE_BIN" -v 2>&1) || version_rc=$?
echo "kore -v output: $version_out (exit $version_rc)"
if [ "$version_rc" -ne 0 ]; then
    echo "FAIL(2/5): kore -v exited with $version_rc" >&2
    exit 1
fi
echo "$version_out" | grep -q "4.2.3" || {
    echo "FAIL(2/5): kore -v output lacks '4.2.3': $version_out" >&2
    exit 1
}
echo "PASS(2/5): kore -v reports 4.2.3"

# Assertion 3: kodev help lists available commands.
if [ ! -x "$KODEV_BIN" ]; then
    echo "FAIL(3/5): kodev binary not executable at $KODEV_BIN" >&2
    ls -la "$KODEV_BIN" >&2 || true
    exit 1
fi
help_out=$("$KODEV_BIN" help 2>&1) || true
echo "$help_out" | grep -q "Available commands" || {
    echo "FAIL(3/5): kodev help lacks 'Available commands': $help_out" >&2
    exit 1
}
echo "PASS(3/5): kodev help lists available commands"

# Assertion 4: public C headers are installed for app development.
if [ ! -f "$PKG_DIR/include/kore/kore.h" ]; then
    echo "FAIL(4/5): missing $PKG_DIR/include/kore/kore.h" >&2
    exit 1
fi
echo "PASS(4/5): include/kore/kore.h installed"

# Assertion 5: build metadata (features/linker) installed for kodev builds.
if [ ! -f "$PKG_DIR/share/kore/features" ]; then
    echo "FAIL(5/5): missing $PKG_DIR/share/kore/features" >&2
    exit 1
fi
echo "PASS(5/5): share/kore/features installed"

echo "PASS: kore 4.2.3 consumer smoke test (5/5)"
