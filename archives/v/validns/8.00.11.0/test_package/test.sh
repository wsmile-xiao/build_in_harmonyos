#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the validns executable.
# Runs in conanrun env (PATH includes the installed bin/).
# R34: genuinely exercises the tested package's binary (Judy + OpenSSL code
# paths) by parsing real zone files, including a threaded run.
set -eu

echo "[test] validns -V (version)"
VER=$(validns -V)
echo "OK: -V reports ${VER}"
# Upstream prints its own PACKAGE_VERSION (0.11.0). The platform version
# 8.00.11.0 is the Debian-style packaging name (8.0+really0.11.0); see
# conandata.yml for the anchor.
[ "${VER}" = "0.11.0" ] || { echo "FAIL: unexpected version string"; exit 1; }

ZONE="$(pwd)/validns-smoke.zone"
cat > "${ZONE}" <<'EOF'
$ORIGIN example.
$TTL 3600
@        IN SOA ns1.example. hostmaster.example. ( 2026092201 86400 3600 604800 3600 )
@        IN NS  ns1.example.
ns1      IN A    192.0.2.1
ns1      IN AAAA 2001:db8::1
@        IN MX   10 mail.example.
mail     IN A    192.0.2.2
@        IN TXT  "validns smoke test on OHOS"
_sip._tcp IN SRV 10 60 5060 sip.example.
sip      IN A    192.0.2.3
EOF

echo "[test] validns single-threaded zone validation"
validns "${ZONE}"
echo "OK: unsigned zone parses clean (rc=0)"

echo "[test] validns threaded validation (-n2, pthread path)"
validns -n2 "${ZONE}"
echo "OK: threaded run parses clean (rc=0)"

echo "[test] validns negative case (bogus RR syntax must fail)"
cat > "${ZONE}.bad" <<'EOF'
$ORIGIN example.
@ IN NOTAREALTYPE "x"
EOF
if validns "${ZONE}.bad" >/dev/null 2>&1; then
    echo "FAIL: invalid zone unexpectedly accepted"
    exit 1
fi
echo "OK: invalid zone rejected as expected"

rm -f "${ZONE}" "${ZONE}.bad"
echo "ALL SMOKE TESTS PASSED"
