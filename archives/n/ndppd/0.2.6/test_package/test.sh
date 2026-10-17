#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the ndppd executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
#
# ndppd has no --version/--help exit path: it always prints a version
# banner first, then tries to load its config file. Pointing -c at a
# nonexistent file makes it exit non-zero after the banner — an ideal
# deterministic smoke check that needs no root, no interfaces and no
# network.
#
# NOTE: upstream 0.2.6 tag still reports NDPPD_VERSION "0.2.4"
# (src/ndppd.h upstream oversight) — assertions must match 0.2.4.
set -eu
set -o pipefail

# E002: /tmp is read-only erofs on OHOS — use $TMPDIR with fallback
OUT="${TMPDIR:-/data/local/tmp}/ndppd-test.out"

set +e
ndppd -c /nonexistent-ndppd-test.conf > "$OUT" 2>&1
rc=$?
set -e

echo "[test] version banner present"
grep -q "ndppd (NDP Proxy Daemon) version 0.2.4" "$OUT"
echo "OK: version banner reports 0.2.6-tag binary"

echo "[test] config path echoed"
grep -q "Using configuration file '/nonexistent-ndppd-test.conf'" "$OUT"
echo "OK: -c option honoured"

echo "[test] exits non-zero on missing config (daemon does not start)"
if [ "$rc" -eq 0 ]; then
    echo "FAIL: expected non-zero exit, got $rc"
    exit 1
fi
echo "OK: exit code $rc as expected (no config / no raw-socket privileges)"

rm -f "$OUT"
echo "ALL OK"
