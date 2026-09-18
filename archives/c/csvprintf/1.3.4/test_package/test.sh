#!/bin/sh
# test_package/test.sh — smoke test for csvprintf executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] csvprintf --version"
csvprintf --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    csvprintf --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ csvprintf failed both --version and --help"
        exit 1
    }
}

echo "[test] csvprintf -h (exit 0)"
csvprintf -h > /dev/null 2>&1 && echo "✅ -h OK" || exit 1

echo "[test] csvprintf basic CSV→XML"
echo 'name,value' | csvprintf -x -i > /tmp/csvprintf-test-xml.out 2>&1
grep -q "<csv>" /tmp/csvprintf-test-xml.out && echo "✅ XML OK" || exit 1

echo "[test] csvprintf basic CSV→JSON"
echo 'name,value' | csvprintf -j -i > /tmp/csvprintf-test-json.out 2>&1
grep -q '\[' /tmp/csvprintf-test-json.out && echo "✅ JSON OK" || exit 1

echo "[test] csvprintf basic CSV→bash"
echo 'name,value' | csvprintf -b -i > /tmp/csvprintf-test-bash.out 2>&1
grep -q "name=" /tmp/csvprintf-test-bash.out && echo "✅ BASH OK" || exit 1

rm -f /tmp/csvprintf-test-*.out
echo "All smoke tests passed"
