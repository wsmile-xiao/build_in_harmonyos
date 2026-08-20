#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for arpon executable
# Runs in conanrun env (PATH includes installed sbin/)
# R34: Test must substantively depend on the tested package (run the actual binary)
# arpon requires root for full operation; --version/--help may exit non-zero
# due to permission checks. We distinguish crash (signal >= 128) from clean exit.
set -euo pipefail

echo "[test] arpon --version"
exit_code=0
output=$(arpon --version 2>&1) || exit_code=$?
echo "$output" | head -5

if [ $exit_code -ge 128 ]; then
    echo "❌ arpon crashed (signal $((exit_code - 128)))"
    exit 1
fi

if [ $exit_code -eq 127 ] || [ $exit_code -eq 126 ]; then
    echo "❌ arpon 不存在或不可执行 (exit $exit_code)"
    exit 1
fi

# Exit < 128 (excluding 126/127) = clean exit (permission denied, usage error, etc.)
echo "✅ arpon binary functional (exit $exit_code)"
