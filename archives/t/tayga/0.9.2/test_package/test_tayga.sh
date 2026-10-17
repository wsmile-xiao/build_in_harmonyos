#!/bin/sh
# Smoke tests for the installed tayga binary (stateless NAT64 daemon).
#
# The full NAT64 data plane needs /dev/net/tun and root, which is out of
# scope here; these assertions exercise the installed CLI:
#   1) tayga resolves from the conanrun environment (package artifacts)
#   2) --help prints the usage text and exits 0
#   3) an invalid option is rejected with a non-zero exit code
set -u

command -v tayga >/dev/null 2>&1 || { echo "FAIL: tayga not found in PATH"; exit 1; }

out=$(tayga --help 2>&1)
rc=$?
[ "$rc" -eq 0 ] || { echo "FAIL: --help exited $rc"; exit 1; }
case "$out" in
    *Usage:*) ;;
    *) echo "FAIL: --help printed no usage text"; exit 1 ;;
esac

if tayga --definitely-not-an-option >/dev/null 2>&1; then
    echo "FAIL: invalid option was accepted"
    exit 1
fi

echo "test_tayga.sh: all assertions passed"
