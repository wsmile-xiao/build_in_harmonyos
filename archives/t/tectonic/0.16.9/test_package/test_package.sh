#!/system/bin/sh
# test_package.sh — tectonic 0.16.9 test script
# Runs tectonic --version to verify the binary is functional.
set -eu
# pipefail may not be available in all shells (e.g., mksh on OHOS)
set -o pipefail 2>/dev/null || true

# The tectonic binary path is provided by Conan
TECTONIC_BIN="${TECTONIC_BIN:-tectonic}"

# Run tectonic --version
output=$("$TECTONIC_BIN" --version 2>&1) || {
    echo "FAIL: tectonic --version failed to execute"
    exit 1
}
echo "$output"

# Verify output contains "Tectonic"
if echo "$output" | grep -q "Tectonic"; then
    echo "PASS: tectonic binary is functional"
    exit 0
else
    echo "FAIL: tectonic --version did not produce expected output"
    exit 1
fi
