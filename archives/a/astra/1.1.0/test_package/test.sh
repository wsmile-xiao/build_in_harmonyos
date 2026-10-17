#!/usr/bin/env bash
# test_package/test.sh — smoke test for astra CLI (Homebrew variant)
# Based on Homebrew formula test block:
#   https://github.com/Homebrew/homebrew-core/blob/HEAD/Formula/a/astra.rb
set -euo pipefail

echo "[test] astra version"
astra version && echo "✅ astra version OK" || {
    echo "❌ astra version failed"
    exit 1
}

echo "[test] astra config path -p"
ASTRARC="/a/b/c" ASTRA_HOME="$(pwd)" astra config path -p && echo "✅ astra config path OK" || {
    echo "❌ astra config path failed"
    exit 1
}

echo "[test] astra db list (with non-existent config)"
# Per 守则: must strictly check exit code == 2, must check "/x/y/z",
# must check "does not exist"; ANY mismatch must raise a test failure.
db_out=$(ASTRARC="/x/y/z" astra db list 2>&1)
db_exit=$?
echo "astra db list → exit=$db_exit out=$(echo "$db_out" | head -1)"
if [ "$db_exit" -ne 2 ]; then
    echo "❌ astra db list expected exit 2, got exit $db_exit"
    exit 1
fi
case "$db_out" in
    *"/x/y/z"*) : ;;
    *)
        echo "❌ astra db list output missing '/x/y/z', got: $db_out"
        exit 1
        ;;
esac
case "$db_out" in
    *"does not exist"*) : ;;
    *)
        echo "❌ astra db list output missing 'does not exist', got: $db_out"
        exit 1
        ;;
esac
echo "✅ astra db list exit 2 + /x/y/z + does not exist OK"

echo "[test] astra compgen"
astra compgen && echo "✅ astra compgen OK" || {
    echo "❌ astra compgen failed"
    exit 1
}

echo "[test] astra smoke test: PASS"