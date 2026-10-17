#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for dash-shell executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] dash -c 'echo hello'"
out=$(dash -c 'echo hello')
[ "$out" = "hello" ] && echo "✅ echo OK" || { echo "❌ echo failed: $out"; exit 1; }

echo "[test] dash -c 'echo \$((3+5))'"
out=$(dash -c 'echo $((3+5))')
[ "$out" = "8" ] && echo "✅ arithmetic OK" || { echo "❌ arithmetic failed: $out"; exit 1; }

echo "[test] dash -c 'f(){ echo \$1; }; f ok'"
out=$(dash -c 'f(){ echo $1; }; f ok')
[ "$out" = "ok" ] && echo "✅ function OK" || { echo "❌ function failed: $out"; exit 1; }

echo "[test] dash -c 'for i in 1 2 3; do echo \$i; done'"
out=$(dash -c 'for i in 1 2 3; do echo $i; done' | tr '\n' ' ')
[ "$out" = "1 2 3 " ] && echo "✅ loop OK" || { echo "❌ loop failed: $out"; exit 1; }

echo "[test] dash -c 'x=world; echo \"hello \$x\"'"
out=$(dash -c 'x=world; echo "hello $x"')
[ "$out" = "hello world" ] && echo "✅ var expansion OK" || { echo "❌ var expansion failed: $out"; exit 1; }

echo "All tests passed!"
