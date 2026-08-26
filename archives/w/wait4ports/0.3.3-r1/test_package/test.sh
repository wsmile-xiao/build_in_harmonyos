#!/usr/bin/env bash
# test_package/test.sh — smoke test for wait4ports executable
# Runs in conanrun env (PATH includes installed bin/)
set -uo pipefail

echo "[step] wait4ports -v"
wait4ports -v && echo "        [ok] -v OK" || {
        echo "        [fail] -v failed"
        exit 1
}

echo "[step] wait4ports (no args -> usage exit 255)"
wait4ports 2>/dev/null && status=0 || status=$?
if [ "$status" -eq 255 ]; then
        echo "        [ok] usage exit 255 OK"
else
        echo "        [fail] expected exit 255, got $status"
        exit 1
fi

echo "[step] wait4ports -q -t 1 -s 1 tcp://127.0.0.1:65535 (timeout -> exit 255)"
wait4ports -q -t 1 -s 1 tcp://127.0.0.1:65535 2>/dev/null && status=0 || status=$?
if [ "$status" -eq 255 ]; then
        echo "        [ok] timeout exit 255 OK"
else
        echo "        [fail] expected exit 255 on timeout, got $status"
        exit 1
fi
