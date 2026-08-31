#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for exiftags executables
# Runs in conanrun env (PATH includes installed bin/)
# R34: genuinely exercises the tested package's binaries.
# No `set -e`: exifcom/exiftime/exiftags return non-zero on usage/error;
# we check explicitly and exit 1 only if assertions fail.
set -u

pass=0
fail=0

# Check 1: exifcom (no args -> usage with Version)
out=$(exifcom < /dev/null 2>&1) || true
if printf '%s\n' "$out" | grep -q "Version: 1.01"; then
    echo "OK: exifcom displays usage with Version 1.01"
    pass=$((pass + 1))
else
    echo "FAIL: exifcom displays usage with Version 1.01"
    echo "  output: $out"
    fail=$((fail + 1))
fi

# Check 2: exiftime (no args -> usage with Version)
out=$(exiftime < /dev/null 2>&1) || true
if printf '%s\n' "$out" | grep -q "Version: 1.01"; then
    echo "OK: exiftime displays usage with Version 1.01"
    pass=$((pass + 1))
else
    echo "FAIL: exiftime displays usage with Version 1.01"
    echo "  output: $out"
    fail=$((fail + 1))
fi

# Check 3: exiftags (no args -> invalid JPEG format)
out=$(exiftags < /dev/null 2>&1) || true
if printf '%s\n' "$out" | grep -q "invalid JPEG format"; then
    echo "OK: exiftags runs and reports invalid JPEG format"
    pass=$((pass + 1))
else
    echo "FAIL: exiftags reports invalid JPEG format"
    echo "  output: $out"
    fail=$((fail + 1))
fi

# Check 4: exifcom on a minimal JPEG (binary doesn't crash)
TMPDIR="${TMPDIR:-/tmp}"
JPEG="$TMPDIR/exiftest_$$.jpg"
printf '\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9' > "$JPEG"
out=$(exifcom "$JPEG" < /dev/null 2>&1)
rc=$?
# A non-crash exit: signal deaths are > 128; anything <= 128 is a normal return.
if [ "$rc" -le 128 ]; then
    echo "OK: exifcom processed a JPEG file without crash (exit $rc)"
    pass=$((pass + 1))
else
    echo "FAIL: exifcom crashed on JPEG file (exit $rc)"
    echo "  output: $out"
    fail=$((fail + 1))
fi
rm -f "$JPEG"

echo "---"
echo "Results: $pass passed, $fail failed"
if [ "$fail" -gt 0 ]; then
    exit 1
fi
echo "ALL TESTS PASSED"
