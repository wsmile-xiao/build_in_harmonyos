#!/bin/bash
# test_package/test.sh — smoke test for apt-dater-host script
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

# 1. Verify the script exists in PATH
echo "[step] checking apt-dater-host in PATH"
command -v apt-dater-host || {
    echo "        [fail] apt-dater-host not found in PATH"
    exit 1
}
echo "        [ok] apt-dater-host found in PATH"

# 2. Verify it's a shell script
file_result=$(file "$(command -v apt-dater-host)" 2>/dev/null || echo "")
echo "[step] file type: $file_result"

# 3. Verify script syntax
echo "[step] checking script syntax (sh -n)"
sh -n "$(command -v apt-dater-host)" && echo "        [ok] syntax OK" || {
    echo "        [fail] syntax check failed"
    exit 1
}

# 4. Verify expected behavior when called without arguments
echo "[step] running apt-dater-host without arguments"
output=$(apt-dater-host 2>&1 || true)  # || true: script exits non-zero on no args
echo "$output" | grep -q "Don't call this script directly" && echo "        [ok] no-args message OK" || {
    echo "        [fail] unexpected output: $output"
    exit 1
}

# 5. Verify invalid command handling
echo "[step] running apt-dater-host with invalid command"
output=$(apt-dater-host --version 2>&1 || true)  # || true: script exits non-zero on invalid cmd
echo "$output" | grep -q "Invalid command" && echo "        [ok] invalid command handling OK" || {
    echo "        [fail] unexpected output for --version: $output"
    exit 1
}

echo "        [ok] All tests passed"
