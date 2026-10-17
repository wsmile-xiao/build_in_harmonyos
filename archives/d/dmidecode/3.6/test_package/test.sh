#!/bin/sh
# test_package/test.sh — dmidecode L2 smoke test
# Verifies the dmidecode binary is installed and reports version info.
# Called by test_package/conanfile.py via self.run().
set -euo pipefail

BIN_PATH="$1"
if [ -z "$BIN_PATH" ]; then
    echo "ERROR: dmidecode binary path not provided"
    exit 1
fi

if [ ! -x "$BIN_PATH" ]; then
    echo "ERROR: dmidecode binary not found or not executable: $BIN_PATH"
    exit 1
fi

# L2 smoke test: verify dmidecode runs and reports version
output=$("$BIN_PATH" --version 2>&1)
echo "$output"

# Assert version string is present
case "$output" in
    *3.6*)
        echo "test.sh: dmidecode --version OK (version 3.6 confirmed)"
        ;;
    *)
        echo "test.sh: FAIL — version 3.6 not found in output"
        exit 1
        ;;
esac
