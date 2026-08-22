#!/bin/sh
# Smoke test for efi-mkuki package
# Usage: test_efi_mkuki.sh <bin_dir>
set -euo pipefail 2>/dev/null || set -eu

BIN_DIR="$1"
SCRIPT="$BIN_DIR/efi-mkuki"

# 1. Check script exists
if [ ! -f "$SCRIPT" ]; then
    echo "FAIL: efi-mkuki not found at $SCRIPT"
    exit 1
fi

# 2. Check executable bit
if [ ! -x "$SCRIPT" ]; then
    echo "FAIL: efi-mkuki is not executable"
    exit 1
fi

# 3. Check shebang line
head -1 "$SCRIPT" | grep -q '^#!.*sh' || {
    echo "FAIL: efi-mkuki has no shell shebang"
    exit 1
}

# 4. bash syntax check
bash -n "$SCRIPT" || {
    echo "FAIL: efi-mkuki has syntax errors"
    exit 1
}

# 5. Run -V and verify version output
output="$("$SCRIPT" -V 2>&1)" || {
    echo "FAIL: efi-mkuki -V exited with error"
    exit 1
}
echo "$output" | grep -q 'efi-mkuki 1\.0\.0' || {
    echo "FAIL: efi-mkuki -V output unexpected: $output"
    exit 1
}

echo "PASS: efi-mkuki smoke test (5 assertions)"
