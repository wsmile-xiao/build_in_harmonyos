#!/bin/sh
# test_package/test.sh -- functional smoke test for the pipemeter binary.
# Runs in conanrun env (PATH includes the installed bin/).
# R34: genuinely exercises the packaged binary (version flag, byte-exact
# stdin->stdout passthrough, -s progress mode, -f file mode) and compares
# real payload bytes, never empty-vs-empty.
# Counts each real case and emits the HMBS_TEST_PACKAGE_RESULT marker.
set -u

PASS=0
FAIL=0

# cd to a writable directory (HMBS TMPDIR; OHOS /tmp may be read-only)
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}" 2>/dev/null || cd .

# ---- Resolve pipemeter binary ----
PIPMETER_BIN=""
if [ -n "${1:-}" ] && [ -f "${1:-}" ]; then
    PIPMETER_BIN="$1"
elif [ -n "${CONAN_PIPMETER_BIN:-}" ] && [ -f "${CONAN_PIPMETER_BIN:-}" ]; then
    PIPMETER_BIN="$CONAN_PIPMETER_BIN"
elif command -v pipemeter >/dev/null 2>&1; then
    PIPMETER_BIN="pipemeter"
fi
if [ -z "$PIPMETER_BIN" ]; then
    echo "[fail] pipemeter binary not found (PATH=$PATH)"
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"/bin/sh test.sh\",\"discovered\":4,\"passedCount\":0}"
    exit 1
fi
echo "[info] testing binary: $PIPMETER_BIN"

# ---- Fixture: deterministic 2 MiB payload, must be non-empty ----
dd if=/dev/zero of=in.bin bs=1024 count=2048 2>/dev/null
if [ ! -s in.bin ]; then
    echo "[fail] fixture in.bin is empty, refusing empty-vs-empty comparison"
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"/bin/sh test.sh\",\"discovered\":4,\"passedCount\":0}"
    exit 1
fi
IN_SIZE=$(wc -c < in.bin | tr -d ' ')
echo "[info] fixture in.bin size: $IN_SIZE bytes"

echo "[test 1/4] pipemeter -V reports version 1.1.5"
if "$PIPMETER_BIN" -V 2> ver.txt; then
    if grep -q "1\.1\.5" ver.txt; then
        PASS=$((PASS + 1))
        echo "[ok] -V prints version 1.1.5"
    else
        FAIL=$((FAIL + 1))
        echo "[fail] -V output unexpected: $(cat ver.txt)"
    fi
else
    FAIL=$((FAIL + 1))
    echo "[fail] -V exited non-zero"
fi

echo "[test 2/4] stdin->stdout passthrough is byte-exact"
if "$PIPMETER_BIN" < in.bin > out.bin 2> rate.log; then
    if cmp -s in.bin out.bin; then
        PASS=$((PASS + 1))
        echo "[ok] 2 MiB passthrough identical (cmp clean)"
    else
        FAIL=$((FAIL + 1))
        echo "[fail] passthrough output differs from input"
    fi
else
    FAIL=$((FAIL + 1))
    echo "[fail] passthrough run exited non-zero"
fi

echo "[test 3/4] -s progress mode keeps data intact and reports percent"
if "$PIPMETER_BIN" -s "$IN_SIZE" < in.bin > out2.bin 2> prog.log; then
    if cmp -s in.bin out2.bin && grep -q "%" prog.log; then
        PASS=$((PASS + 1))
        echo "[ok] -s mode data identical and progress percent shown"
    else
        FAIL=$((FAIL + 1))
        echo "[fail] -s mode data or progress output wrong"
    fi
else
    FAIL=$((FAIL + 1))
    echo "[fail] -s mode run exited non-zero"
fi

echo "[test 4/4] -f file mode copies file content to stdout"
if "$PIPMETER_BIN" -f in.bin > out3.bin 2> filemode.log; then
    if cmp -s in.bin out3.bin; then
        PASS=$((PASS + 1))
        echo "[ok] -f mode output identical to input file"
    else
        FAIL=$((FAIL + 1))
        echo "[fail] -f mode output differs from input file"
    fi
else
    FAIL=$((FAIL + 1))
    echo "[fail] -f mode run exited non-zero"
fi

rm -f in.bin out.bin out2.bin out3.bin ver.txt rate.log prog.log filemode.log

if [ "$FAIL" -eq 0 ]; then
    PASSED=true
else
    PASSED=false
fi
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$PASSED,\"command\":\"/bin/sh test.sh\",\"discovered\":4,\"passedCount\":$PASS}"
if [ "$FAIL" -ne 0 ]; then
    echo "[fail] $FAIL case(s) failed, $PASS passed"
    exit 1
fi
echo "[ok] all $PASS test_package cases passed"
