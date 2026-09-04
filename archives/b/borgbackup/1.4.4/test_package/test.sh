#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for borgbackup package
# Runs in conanrun env (PATH includes installed bin/)
#
# Note: On OpenHarmony, C extension .so files require ELF signing before
# they can be loaded. This is handled by the CI sign.sh step after packaging.
# This test verifies package structure and attempts borg --version.
set -euo pipefail

# Find the site-packages directory from the borg script location
BORG_BIN=$(which borg 2>/dev/null || echo "")
if [ -z "$BORG_BIN" ]; then
    echo "[fail] borg not found in PATH"
    exit 1
fi

# Resolve symlinks and find package root (quote all substitutions)
BORG_REAL=$(readlink -f "$BORG_BIN" 2>/dev/null || echo "$BORG_BIN")
PKG_ROOT=$(dirname "$(dirname "$(dirname "$BORG_REAL")")")

# Set PYTHONPATH to include site-packages
for pyver in python3.12 python3.13 python3.14; do
    SP="$PKG_ROOT/usr/lib/$pyver/site-packages"
    if [ -d "$SP" ]; then
        export PYTHONPATH="$SP:${PYTHONPATH:-}"
        break
    fi
done

# Also set LD_LIBRARY_PATH for shared libraries
export LD_LIBRARY_PATH="${PKG_ROOT}/usr/lib:${LD_LIBRARY_PATH:-}"

echo "[step] Verify borg binary exists"
if test -f "$BORG_REAL"; then
    echo "        [ok] borg binary found"
else
    echo "        [fail] borg binary not found"
    exit 1
fi

echo "[step] Verify C extension .so files exist"
SO_COUNT=$(find "$PKG_ROOT/usr/lib" -name "*.so" 2>/dev/null | wc -l)
if [ "$SO_COUNT" -gt 0 ]; then
    echo "        [ok] Found $SO_COUNT C extension .so files"
else
    echo "        [fail] No C extension .so files found"
    exit 1
fi

echo "[step] Attempt borg --version (may fail on OHOS without ELF signing)"
if borg --version 2>/dev/null; then
    echo "        [ok] borg --version succeeded"
else
    echo "        [ok] borg --version failed (expected on OHOS without ELF signing)"
    echo "        [step] Verify Python package import instead"
    python3 -c "
import sys
sys.path.insert(0, '$SP')
import borg
assert borg.__version__ == '1.4.4', f'Expected 1.4.4, got {borg.__version__}'
print(f'        [ok] borg version: {borg.__version__}')
" 2>/dev/null || {
    echo "        [fail] borg Python package import failed"
    exit 1
}
fi
