#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for atlantis executable
# Runs in conanrun env (PATH includes installed bin/)
# R34: genuinely invokes the packaged atlantis binary; fails if it
# is missing or does not report its version.
set -euo pipefail

echo "[test] atlantis version"
out="$(atlantis version 2>&1)"
echo "        output: $out"
case "$out" in
  *atlantis*)
    echo "        [ok] version output contains 'atlantis'"
    ;;
  *)
    echo "        [fail] version output missing 'atlantis'"
    exit 1
    ;;
esac

case "$out" in
  *[Pp][Ll][Aa][Cc][Ee][Hh][Oo][Ll][Dd][Ee][Rr]*)
    echo "        [fail] PLACEHOLDER binary detected — genuine Go build required"
    exit 1
    ;;
  *)
    echo "        [ok] no placeholder marker"
    ;;
esac
