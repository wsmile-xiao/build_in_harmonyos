#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the ocat executable (onioncat 4.11.0)
# Runs in conanrun env (PATH includes the installed bin/).
# R34: genuinely exercises the tested package's binary — the three offline
# conversion modes (-i onion->IPv6, -o IPv6->onion, -h usage) are ocat's
# self-contained core functionality that needs neither root nor a TUN device
# nor a running Tor daemon.
set -eu

OCAT="$(command -v ocat)"
if [ -z "${OCAT}" ]; then
    echo "FAIL: ocat not found on PATH"
    exit 1
fi
echo "[test] found ocat at ${OCAT}"

# --- 1. usage banner: contains version string -----------------------------
OUT="$("${OCAT}" -h 2>&1)" || true
if ! echo "${OUT}" | grep -q "onioncat 4.11.0"; then
    echo "FAIL: version banner missing"
    echo "${OUT}"
    exit 1
fi
echo "OK: version banner contains 'onioncat 4.11.0'"

if ! echo "${OUT}" | grep -q "usage:"; then
    echo "FAIL: usage text missing"
    echo "${OUT}"
    exit 1
fi
echo "OK: usage text present"

# --- 2. onion hostname -> IPv6 conversion (-i, v3 56-char base32 form) ----
# Upstream OnionCat prefix fd87:d87e:eb43 (Tor RFC-allowed ULA range).
IPV6="$("${OCAT}" -i pg6mmjiyjmcrss7s5vnevg2v5i2fdeywiy7d7n5o4zr7hkyi4vlggkid.onion)"
if [ "${IPV6}" != "fd87:d87e:eb43:e663:f3ab:8e5:5663:2903" ]; then
    echo "FAIL: -i conversion returned '${IPV6}'"
    exit 1
fi
echo "OK: -i onion->IPv6 conversion = ${IPV6}"

# --- 3. IPv6 -> onion hostname conversion (-o, reverse of #2) -------------
ONION="$("${OCAT}" -o fd87:d87e:eb43:e663:f3ab:8e5:5663:2903)"
if [ "${ONION}" != "4zr7hkyi4vlggkid.onion" ]; then
    echo "FAIL: -o conversion returned '${ONION}'"
    exit 1
fi
echo "OK: -o IPv6->onion conversion = ${ONION}"

# --- 4. invalid input is rejected with nonzero exit -----------------------
if "${OCAT}" -i this-is-not-an-onion-name.onion >/dev/null 2>&1; then
    echo "FAIL: invalid hostname unexpectedly accepted"
    exit 1
fi
echo "OK: invalid input rejected with nonzero exit"

echo "[test] ocat smoke test passed (4 assertions)"
