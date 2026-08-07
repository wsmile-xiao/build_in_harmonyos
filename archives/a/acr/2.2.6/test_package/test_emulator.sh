#!/system/bin/sh
set -u

PACKAGE_ROOT=${1:?usage: test_emulator.sh PACKAGE_ROOT}
ACR=${PACKAGE_ROOT}/bin/acr
WORK_ROOT=/data/local/tmp/acr-2.2.6-test-$$

fail() {
    echo "FAIL: $1"
    exit 1
}

[ -f "${ACR}" ] || fail "packaged acr script is missing"
echo "PASS 1/7: packaged acr script exists"

VERSION_OUTPUT=$(/system/bin/sh "${ACR}" -v 2>&1) || fail "acr -v returned non-zero"
echo "PASS 2/7: acr -v returned zero"
echo "${VERSION_OUTPUT}" | grep -q "2.2.6" || fail "version output does not contain 2.2.6"
echo "PASS 3/7: version is 2.2.6"

mkdir -p "${WORK_ROOT}" || fail "cannot create test directory"
cd "${WORK_ROOT}" || fail "cannot enter test directory"
printf 'PKGNAME sample\nVERSION 1.0\n' > configure.acr

/system/bin/sh "${ACR}" > generate.log 2>&1 || fail "configure generation failed"
echo "PASS 4/7: configure generation returned zero"
if grep -E "inaccessible or not found|arithmetic expression|FAIL" generate.log >/dev/null 2>&1; then
    cat generate.log
    fail "configure generation logged a hidden runtime error"
fi
[ -f configure ] || fail "configure was not generated"
echo "PASS 5/7: configure file exists"
/system/bin/sh configure > configure.log 2>&1 || fail "generated configure failed"
if grep -E "inaccessible or not found|arithmetic expression|FAIL" configure.log >/dev/null 2>&1; then
    cat configure.log
    fail "generated configure logged a hidden runtime error"
fi
echo "PASS 6/7: generated configure returned zero"

if /system/bin/sh "${ACR}" does-not-exist.acr > missing.log 2>&1; then
    fail "missing input unexpectedly succeeded"
fi
echo "PASS 7/7: missing-input fault injection failed as expected"

cd /data/local/tmp || exit 1
rm -rf "${WORK_ROOT}"
echo "RESULT: 7/7 assertions passed"
