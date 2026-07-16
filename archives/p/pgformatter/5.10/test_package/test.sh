#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke + functional test for pg_format
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] pg_format --version"
pg_format --version

echo "[test] format a SQL statement via stdin"
out=$(echo "select a,b from foo where x=1;" | pg_format -)
echo "$out"
echo "$out" | grep -q "SELECT" || {
    echo "❌ pg_format did not produce formatted SQL"
    exit 1
}
echo "✅ pg_format formatted SQL correctly"
