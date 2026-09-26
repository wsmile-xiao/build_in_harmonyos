#!/bin/sh
# Consumer assertions for the packaged spnavd (real executions).
set -u
fails=0

SD="$(command -v spacenavd)" || { echo "FAIL: spnavd not in runenv PATH"; exit 1; }
echo "[1] packaged binary resolves in runenv PATH: $SD"

out="$("$SD" -V 2>&1)"; rc=$?
case "$out" in
  *1.3.1*) : ;;
  *) echo "FAIL: -V output lacks version: $out"; fails=$((fails+1)) ;;
esac
[ "$rc" -eq 0 ] || { echo "FAIL: -V must exit zero"; fails=$((fails+1)); }
echo "[2] -V prints version and exits zero (rc=$rc)"

out="$("$SD" -h 2>&1)"; rc=$?
case "$out" in
  *usage:*) : ;;
  *) echo "FAIL: -h output lacks usage: $out"; fails=$((fails+1)) ;;
esac
echo "[3] -h prints usage (rc=$rc)"

"$SD" -Z >/dev/null 2>&1; rc=$?
[ "$rc" -ne 0 ] || { echo "FAIL: invalid option -Z must be rejected"; fails=$((fails+1)); }
echo "[4] invalid option -Z rejected (rc=$rc)"

if [ "$fails" -eq 0 ]; then
  echo "consumer assertions: 4/4 PASS"
else
  echo "consumer assertions: FAILED ($fails)"
  exit 1
fi
