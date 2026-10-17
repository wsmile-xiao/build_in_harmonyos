#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer test for cbmconvert 2.1.6.
# Runs in conanrun env (PATH includes <package>/bin). Modeled on the upstream
# small_files CTest script: build a 1541 image from files, then convert it
# back to Lynx format. Artifacts stay in a scratch directory.
set -uo pipefail

WORK="${TMPDIR:-$(pwd)}/cbmconvert_test_package_$$"
mkdir -p "$WORK"
cd "$WORK"
trap 'rm -rf "$WORK"' EXIT

failures=0

# [1] Bare invocation prints usage and exits non-zero (upstream marks the
# usage tests WILL_FAIL, i.e. expects failure). Output is captured first so
# pipefail/SIGPIPE races cannot affect the match.
cbmconvert >/dev/null 2>&1
rc=$?
banner="$(cbmconvert 2>&1 || true)"
case "$banner" in
    *"cbmconvert 2.1.6"*)
        if [ $rc -ne 0 ]; then
            echo "assert 1 OK: usage banner, non-zero exit ($rc)"
        else
            echo "assert 1 FAIL: banner present but rc=$rc (expected non-zero)"
            failures=$((failures + 1))
        fi
        ;;
    *)
        echo "assert 1 FAIL: banner missing (rc=$rc)"
        failures=$((failures + 1))
        ;;
esac

# [2] Real behavior: write two files into a fresh 1541 image (-D4).
printf '1' > "1,S"
printf '12' > "2,U"
cbmconvert -D4 test.d64 "1,S" "2,U"
rc=$?
size="$(wc -c < test.d64)"
if [ $rc -eq 0 ] && [ "$size" -eq 174848 ]; then
    echo "assert 2 OK: D64 created, 174848 bytes"
else
    echo "assert 2 FAIL: rc=$rc size=$size"
    failures=$((failures + 1))
fi

# [3] Convert the image back to a Lynx archive (-L ... -d).
cbmconvert -L out.lnx -d test.d64
rc=$?
lnxsize="$(wc -c < out.lnx)"
if [ $rc -eq 0 ] && [ "$lnxsize" -gt 0 ]; then
    echo "assert 3 OK: Lynx archive written ($lnxsize bytes)"
else
    echo "assert 3 FAIL: rc=$rc lnxsize=$lnxsize"
    failures=$((failures + 1))
fi

# [4] Companion tools exist and are runnable (usage exit is non-zero).
disk2zip >/dev/null 2>&1; rc1=$?
zip2disk >/dev/null 2>&1; rc2=$?
if [ $rc1 -ne 0 ] && [ $rc2 -ne 0 ]; then
    echo "assert 4 OK: disk2zip/zip2disk usage exits non-zero"
else
    echo "assert 4 FAIL: disk2zip rc=$rc1 zip2disk rc=$rc2 (expected non-zero)"
    failures=$((failures + 1))
fi

if [ $failures -ne 0 ]; then
    echo "cbmconvert consumer test: $failures assertion group(s) FAILED"
    exit 1
fi
echo "cbmconvert consumer test: 4/4 assertion groups passed"
