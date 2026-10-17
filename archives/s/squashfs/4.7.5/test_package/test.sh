#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for squashfs executable
# Runs in conanrun env (PATH includes installed bin/)
# Note: unsquashfs --version exits with non-zero status even on success
set -eu

echo "[test] mksquashfs --version"
mksquashfs --version 2>&1 | head -1 | grep -q "version" && echo "✅ mksquashfs --version OK" || {
    echo "❌ mksquashfs --version failed"
    exit 1
}

echo "[test] unsquashfs --version"
unsquashfs --version 2>&1 | head -1 | grep -q "version" && echo "✅ unsquashfs --version OK" || {
    echo "❌ unsquashfs --version failed"
    exit 1
}
