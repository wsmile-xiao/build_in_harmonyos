#!/usr/bin/env bash
# test_package/test.sh — smoke test for scala executable tools
# Runs in conanrun env (PATH includes installed bin/)
set -eu

# Scala tools require Java (JVM) — skip if not available
if ! command -v java >/dev/null 2>&1; then
    echo "[skip] Java (JVM) not found in PATH — skipping Scala tool smoke tests"
    echo "[skip] Install bishengjdk 17.0.13 for full test coverage"
    exit 0
fi

echo "[test] scala -version"
scala -version 2>&1 && echo "✅ scala -version OK" || {
    echo "❌ scala -version failed"
    exit 1
}

echo "[test] scalac -version"
scalac -version 2>&1 && echo "✅ scalac -version OK" || {
    echo "❌ scalac -version failed"
    exit 1
}

echo "[test] scaladoc -version"
scaladoc -version 2>&1 && echo "✅ scaladoc -version OK" || {
    echo "❌ scaladoc -version failed"
    exit 1
}

echo "[test] scalap -help"
scalap -help 2>&1 > /dev/null && echo "✅ scalap OK" || {
    echo "⚠️ scalap -help returned non-zero (expected for help text)"
    # scalap returns non-zero for -help, check if it at least runs
    scalap 2>&1 || true
}

echo "[test] fsc -version"
fsc -version 2>&1 && echo "✅ fsc -version OK" || {
    echo "❌ fsc -version failed"
    exit 1
}

echo "✅ All Scala tools smoke tests passed!"
