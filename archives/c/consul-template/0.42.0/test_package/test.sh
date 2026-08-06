#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for consul-template executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] consul-template --version"
consul-template --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    consul-template --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ consul-template failed both --version and --help"
        exit 1
    }
}

# Verify version string contains expected version number
echo "[test] verifying version string..."
VERSION_OUTPUT=$(consul-template --version 2>&1)
if echo "$VERSION_OUTPUT" | grep -q "0.42.0"; then
    echo "✅ version string contains 0.42.0"
else
    echo "❌ version string does not contain expected version: $VERSION_OUTPUT"
    exit 1
fi
