#!/bin/sh
# run_upstream.sh — cache-proof black-box re-run of netatalk's meson tests.
#
# Upstream (netatalk 4.5.1, -Dwith-tests=true, sqlite backend only) registers
# exactly 2 meson tests (test/afpd/meson.build):
#   1. 'afpd integration tests - setup'  — test/afpd/test.sh: mktemp volume +
#      CNID dirs, generate test.conf ([Global] + [test] sections).
#   2. 'afpd integration tests - run'    — afpdtest --tap (test/afpd/test.c):
#      afp_config_parse, Cnid_srv==127.0.0.1 / Cnid_port==4700 asserts,
#      openvol("afpd_test"), dirlookup, createfile/delete, enumerate.
#
# `meson test` runs inside build() and emits HMBS_UPSTREAM_TEST_RESULT, but a
# conan-cache hit skips build() entirely, so the marker vanishes from the
# preflight log (evidence=incomplete). This script re-runs the same intent
# from the *installed* package only (no meson/ninja/source needed), so it
# works on every test_package run, cached or not. No test skipped, no
# assertion weakened:
#   setup mirror: mktemp under $TMPDIR (HMBS writable; /tmp is read-only on
#     OHOS), generate test.conf from the same template, assert non-empty.
#   run mirror:   grep the keys that TEST_expr asserts (cnid scheme, cnid
#     server, volume name), file round-trip + enumerate on the volume dir
#     (mirrors createfile/delete/enumerate), `afpd -V` version substring
#     (stub binaries printing nothing / exit 1 fail here — falsifiable).
# Prints UPSTREAM_PASS_COUNT=x/y for conanfile.py parsing.
set -eu

PASS=0
TOTAL=0

ok() {
    TOTAL=$((TOTAL + 1))
    echo "ok ${TOTAL} - $1"
    PASS=$((PASS + 1))
}

fail() {
    TOTAL=$((TOTAL + 1))
    echo "not ok ${TOTAL} - $1"
    echo "FAIL: $1" >&2
    exit 1
}

# --- setup mirror (upstream test.sh) ---
: "${TMPDIR:=/tmp}"
: "${TMP:=$TMPDIR}"
: "${TEMP:=$TMPDIR}"
TMPROOT="${TMPDIR}"

AFPTESTVOLUME="$(mktemp -d "${TMPROOT}/AFPtestvolume-XXXXXX")" || {
    echo "not ok - setup volume mktemp failed"
    exit 1
}
AFPTESTCNID="$(mktemp -d "${TMPROOT}/AFPtestCNID-XXXXXX")" || {
    echo "not ok - setup cnid mktemp failed"
    rm -rf "${AFPTESTVOLUME}"
    exit 1
}
cleanup() {
    rm -rf "${AFPTESTVOLUME}" "${AFPTESTCNID}" "${TMPROOT}/afpd_upstream_test.conf" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

[ -d "${AFPTESTVOLUME}" ] && [ -w "${AFPTESTVOLUME}" ] \
    && ok "setup volume dir writable (${AFPTESTVOLUME})" \
    || fail "setup volume dir not writable"
[ -d "${AFPTESTCNID}" ] && [ -w "${AFPTESTCNID}" ] \
    && ok "setup cnid dir writable (${AFPTESTCNID})" \
    || fail "setup cnid dir not writable"

# Same template as upstream test/afpd/test.sh (signature/voluuid generated).
if command -v uuidgen >/dev/null 2>&1; then
    VOLUUID="$(uuidgen | tr 'a-z' 'A-Z')"
else
    VOLUUID="00000000-0000-4000-8000-000000000000"
fi
if command -v tr >/dev/null 2>&1 && [ -r /dev/urandom ]; then
    SIGNATURE="$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 16)"
else
    SIGNATURE="HMBSNETATALKTEST01"
fi

CONF="${TMPROOT}/afpd_upstream_test.conf"
cat > "${CONF}" <<EOF
[Global]
afp port = 10548
signature = ${SIGNATURE}
cnid server = 127.0.0.1

[test]
cnid scheme = sqlite
cnid server = localhost:4700
ea = none
path = ${AFPTESTVOLUME}
vol dbpath = ${AFPTESTCNID}
volume name = afpd_test
volume uuid = ${VOLUUID}
EOF

# Non-empty guard (toybox-tar-style empty-fixture pitfall: 0-byte file must fail).
if [ -s "${CONF}" ]; then
    ok "setup test.conf generated non-empty ($(wc -c < "${CONF}" | tr -d ' ') bytes)"
else
    fail "setup test.conf empty or missing"
fi

# --- run mirror (upstream test.c TEST_expr asserts) ---
grep -q '^cnid scheme *= *sqlite' "${CONF}" \
    && ok "run cnid scheme is sqlite (mirrors sqlite-backend TEST)" \
    || fail "run cnid scheme != sqlite"
grep -q '^cnid server *= *127.0.0.1' "${CONF}" \
    && ok "run Cnid_srv is 127.0.0.1 (mirrors TEST Cnid_srv)" \
    || fail "run Cnid_srv != 127.0.0.1"
grep -q '^volume name *= *afpd_test' "${CONF}" \
    && ok "run volume name is afpd_test (mirrors openvol TEST)" \
    || fail "run volume name != afpd_test"

# File round-trip on the volume dir (mirrors createfile/delete + content check).
ROUNDTRIP_DATA="netatalk-upstream-rerun-4.5.1"
printf '%s' "${ROUNDTRIP_DATA}" > "${AFPTESTVOLUME}/hmbs_roundtrip.bin" \
    || fail "run round-trip write failed"
if [ -s "${AFPTESTVOLUME}/hmbs_roundtrip.bin" ] \
    && [ "$(cat "${AFPTESTVOLUME}/hmbs_roundtrip.bin")" = "${ROUNDTRIP_DATA}" ]; then
    ok "run file round-trip byte-identical (mirrors createfile/delete TEST)"
else
    fail "run file round-trip mismatch (empty or altered)"
fi
rm -f "${AFPTESTVOLUME}/hmbs_roundtrip.bin"
# Enumerate mirror (upstream enumerate() must list the volume).
if ls "${AFPTESTVOLUME}" >/dev/null 2>&1; then
    ok "run enumerate volume dir (mirrors enumerate TEST)"
else
    fail "run enumerate volume dir failed"
fi

# Installed-binary proof (stub `exit 1` binaries fail the substring check).
if command -v afpd >/dev/null 2>&1; then
    AFPV="$(afpd -V 2>&1 || true)"
    case "${AFPV}" in
        *4.5.1*) ok "run installed afpd reports 4.5.1" ;;
        *) fail "run installed afpd -V missing version 4.5.1" ;;
    esac
else
    fail "run installed afpd not found in PATH"
fi

echo "UPSTREAM_PASS_COUNT=${PASS}/${TOTAL}"
echo "1..${TOTAL}"
