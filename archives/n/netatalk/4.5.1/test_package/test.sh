#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the netatalk executables
# Runs in conanrun env (PATH includes the installed bin/ and sbin/).
# R34: genuinely exercises the tested package's binaries.
set -euo pipefail

pass_count=0

check_version() {
    bin_name="$1"
    echo "[test] ${bin_name} -V (version check)"
    if ! command -v "${bin_name}" >/dev/null 2>&1; then
        echo "FAIL: ${bin_name} not found in PATH"
        exit 1
    fi
    # Tolerate non-zero exit when the version string is present (daemons
    # may return 1 after printing --help/-V); only the version substring
    # decides pass/fail. An exec-blocked binary (Operation not permitted)
    # prints no version and still fails here.
    set +e
    output="$("${bin_name}" -V 2>&1)"
    status=$?
    set -e
    echo "${output}" | grep -q "4.5.1" || {
        echo "FAIL: ${bin_name} -V output missing version 4.5.1 (exit ${status}): ${output}"
        exit 1
    }
    echo "OK: ${bin_name} reports 4.5.1 (exit ${status})"
    pass_count=$((pass_count + 1))
}

check_version "afpd"
# NOTE: cnid_dbd/cnid_metad are only built with the Berkeley DB backend
# (etc/meson.build: `if use_dbd_backend` → subdir('cnid_dbd')). This recipe
# builds sqlite-only, so they do not exist; `dbd` (bin/dbd, always built,
# `dbd -V` prints "dbd <version>") is the CNID tool covered here instead.
check_version "dbd"
check_version "netatalk"

echo "[test] afppasswd presence check"
command -v afppasswd >/dev/null 2>&1 || {
    echo "FAIL: afppasswd not found in PATH"
    exit 1
}
echo "OK: afppasswd present"
pass_count=$((pass_count + 1))

echo "PASS: netatalk smoke test (${pass_count}/4 checks passed)"
