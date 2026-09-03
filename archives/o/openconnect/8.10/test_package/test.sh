#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the openconnect executable package
# Runs in conanrun env (LD_LIBRARY_PATH includes the gnutls/libxml2/zlib
# runtime libs pulled from the requirements graph by VirtualRunEnv).
set -eu -o pipefail

echo "[test] "${OPENCONNECT_BIN:-openconnect}" --version"
"${OPENCONNECT_BIN:-openconnect}" --version

echo "[test] verify version string contains 8.10"
"${OPENCONNECT_BIN:-openconnect}" --version | grep -q "v8.10" || {
    echo "[fail] version banner does not contain v8.10"
    exit 1
}

echo "[test] verify GnuTLS feature line"
"${OPENCONNECT_BIN:-openconnect}" --version | grep -q "GnuTLS" || {
    echo "[fail] GnuTLS banner missing"
    exit 1
}

echo "[test] verify supported protocols line"
"${OPENCONNECT_BIN:-openconnect}" --version | grep -q "anyconnect" || {
    echo "[fail] anyconnect protocol missing"
    exit 1
}

echo "[test] all smoke assertions passed"
