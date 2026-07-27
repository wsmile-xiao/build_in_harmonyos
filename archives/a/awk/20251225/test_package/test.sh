#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for awk executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] awk --version"
awk --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying -V..."
    awk -V 2>/dev/null && echo "✅ -V OK" || {
        echo "[test] -V also failed, trying basic functionality..."
        echo "hello world" | awk '{print $1}' | grep -q "hello" && echo "✅ basic functionality OK" || {
            echo "❌ awk failed all version and functionality checks"
            exit 1
        }
    }
}

echo "[test] basic text processing"
result=$(echo "hello world" | awk '{print $1}')
if [ "$result" = "hello" ]; then
    echo "✅ field extraction OK"
else
    echo "❌ field extraction failed: got '$result'"
    exit 1
fi

echo "[test] regex substitution"
result=$(echo "foo123bar" | awk '{gsub(/[0-9]+/, "NUM"); print}')
if [ "$result" = "fooNUMbar" ]; then
    echo "✅ gsub OK"
else
    echo "❌ gsub failed: got '$result'"
    exit 1
fi

echo "[test] array counting"
result=$(printf "a\nb\na\nc\n" | awk '{count[$1]++} END {for(k in count) print k, count[k]}' | sort)
expected="a 2
b 1
c 1"
if [ "$result" = "$expected" ]; then
    echo "✅ array counting OK"
else
    echo "❌ array counting failed: got '$result'"
    exit 1
fi

echo "✅ All smoke tests passed"
