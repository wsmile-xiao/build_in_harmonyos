#!/usr/bin/env bash
# test_package/test.sh — smoke test for the etsh executable
# Runs in conanrun env (PATH includes installed bin/)
# R34: genuinely exercises the tested package's binary.
set -euo pipefail

echo "[test] etsh -c 'echo test'"
out="$(etsh -c 'echo test' 2>&1)" || {
    echo "FAIL: etsh -c 'echo test' exited $?"
    exit 1
}
echo "$out" | grep -q '^test$' && echo "OK: etsh -c 'echo test' → 'test'" || {
    echo "FAIL: expected 'test', got: $out"
    exit 1
}

echo "[test] etsh -c 'echo \$\$' (PID substitution)"
out2="$(etsh -c 'echo $$' 2>&1)" || {
    echo "FAIL: etsh -c 'echo \$\$' exited $?"
    exit 1
}
echo "OK: etsh reported PID $out2"

echo "[test] etsh version banner via -v or builtin"
# etsh has no --version flag; verify it runs a simple pipeline
out3="$(etsh -c 'echo hello | cat' 2>&1)" || {
    echo "FAIL: pipeline test exited $?"
    exit 1
}
echo "$out3" | grep -q '^hello$' && echo "OK: pipeline works" || {
    echo "FAIL: pipeline expected 'hello', got: $out3"
    exit 1
}

echo "All etsh smoke tests passed."
