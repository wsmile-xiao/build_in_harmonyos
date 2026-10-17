#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the rtorrent executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -eu

echo "[test] rtorrent -h prints usage and exits 0"
usage=$(rtorrent -h 2>&1)
case "$usage" in
  *"Rakshasa's BitTorrent client"*) echo "OK: banner found" ;;
  *) echo "FAIL: banner missing from -h output"; exit 1 ;;
esac
case "$usage" in
  *"Usage: rtorrent"*) echo "OK: usage line found" ;;
  *) echo "FAIL: usage line missing from -h output"; exit 1 ;;
esac

echo "[test] rtorrent -n -h skips rtorrent.rc and still exits 0"
rtorrent -n -h > /dev/null 2>&1
echo "OK: exit code 0"

echo "ALL TESTS PASSED"
