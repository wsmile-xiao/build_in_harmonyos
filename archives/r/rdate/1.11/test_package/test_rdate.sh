#!/bin/sh
# Consumer assertions for the packaged rdate 1.11 (real executions).
set -u
fails=0

RD="$(command -v rdate)" || { echo "FAIL: rdate not in runenv PATH"; exit 1; }
echo "[1] packaged binary resolves in runenv PATH: $RD"

out="$("$RD" 2>&1)"; rc=$?
case "$out" in
  *"Usage: "*) : ;;
  *) echo "FAIL: no-args output lacks Usage text: $out"; fails=$((fails+1)) ;;
esac
[ "$rc" -ne 0 ] || { echo "FAIL: no-args must exit nonzero"; fails=$((fails+1)); }
echo "[2] no-args prints usage and exits nonzero (rc=$rc)"

"$RD" -Z 127.0.0.1 >/dev/null 2>&1; rc=$?
[ "$rc" -ne 0 ] || { echo "FAIL: invalid option -Z must be rejected"; fails=$((fails+1)); }
echo "[3] invalid option rejected (rc=$rc)"

out="$("$RD" -p -o 1 127.0.0.1 2>&1)"; rc=$?
[ "$rc" -ne 0 ] || { echo "FAIL: RFC868 query to a closed loopback port must fail"; fails=$((fails+1)); }
echo "[4] closed-port query fails cleanly (rc=$rc): $(echo "$out" | head -1)"

if [ "$fails" -eq 0 ]; then
  echo "consumer assertions: 4/4 PASS"
else
  echo "consumer assertions: FAILED ($fails)"
  exit 1
fi
