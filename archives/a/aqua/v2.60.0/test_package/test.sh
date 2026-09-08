#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for aqua executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] aqua --version"
aqua --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying version subcommand..."
    aqua version && echo "✅ version OK" || {
        echo "[test] version failed, trying --help..."
        aqua --help > /dev/null 2>&1 && echo "✅ --help OK" || {
            echo "❌ aqua failed --version, version, and --help"
            exit 1
        }
    }
}

# Verify version string contains expected version number
echo "[test] verifying version string..."
VERSION_OUTPUT=$(aqua --version 2>&1 || aqua version 2>&1)
if echo "$VERSION_OUTPUT" | grep -q "2.60.0"; then
    echo "✅ version string contains 2.60.0"
else
    echo "❌ version string does not contain expected version: $VERSION_OUTPUT"
    exit 1
fi
