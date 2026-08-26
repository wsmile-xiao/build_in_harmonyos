#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for zonenotify executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

# Check that zonenotify binary exists in PATH
if ! command -v zonenotify > /dev/null 2>&1; then
    echo "❌ zonenotify binary not found in PATH"
    exit 1
fi

echo "[test] zonenotify found: $(command -v zonenotify)"

# Run zonenotify without args - it should print version + usage and exit 1
output=$(zonenotify 2>&1 || true)

# Verify the output contains the specific version string from the binary
echo "$output" | grep -q "zonenotify 0.01" && echo "✅ version string found" || {
    echo "❌ zonenotify output does not contain expected version string"
    echo "Output was: $output"
    exit 1
}
