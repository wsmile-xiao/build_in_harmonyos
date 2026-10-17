#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for rc executable
# Runs in conanrun env (PATH includes installed bin/)
# rc doesn't support --version (uses $version variable), so we test
# that rc can execute a simple echo command.
set -euo pipefail

echo "[test] rc -c 'echo hello'"
output=$(rc -c 'echo hello' 2>&1) || {
    echo "❌ rc -c 'echo hello' failed with exit code $?"
    exit 1
}
if [ "$output" = "hello" ]; then
    echo "✅ rc -c 'echo hello' output matches: $output"
else
    echo "❌ rc -c 'echo hello' output mismatch: expected 'hello', got '$output'"
    exit 1
fi

echo "[test] rc -c 'echo \$version'"
output=$(rc -c 'echo $version' 2>&1) || {
    echo "❌ rc -c 'echo \$version' failed with exit code $?"
    exit 1
}
if [ -n "$output" ]; then
    echo "✅ rc version variable: $output"
else
    echo "❌ rc version variable is empty"
    exit 1
fi

echo "✅ All rc smoke tests passed"
