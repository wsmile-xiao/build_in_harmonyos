#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for muscle executable
# Runs in conanrun env (PATH includes installed bin/)
# On OHOS, unsigned binaries may fail with "Operation not permitted";
# this is expected — CI signs the binary before testing.
# OHOS /tmp is read-only; use $TMPDIR instead.

TMPDIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPDIR" 2>/dev/null || true
ERR_FILE="$TMPDIR/muscle_test_err.txt"

echo "[test] muscle --version"

# Try to run muscle --version
muscle --version 2>"$ERR_FILE"
ret=$?

if [ $ret -eq 0 ]; then
    echo "✅ --version OK"
    exit 0
fi

# Check if the error is "Operation not permitted" (OHOS ELF signing)
if grep -qi "Operation not permitted" "$ERR_FILE" 2>/dev/null; then
    echo "⚠️  muscle binary present but unsigned (OHOS ELF signing required)"
    echo "    This is expected on local device; CI signs via sign.sh"
    exit 0
fi

# Try --help as fallback
ERR_FILE2="$TMPDIR/muscle_test_err2.txt"
muscle --help > /dev/null 2>"$ERR_FILE2"
ret2=$?
if [ $ret2 -eq 0 ]; then
    echo "✅ --help OK"
    exit 0
fi

if grep -qi "Operation not permitted" "$ERR_FILE2" 2>/dev/null; then
    echo "⚠️  muscle binary present but unsigned (OHOS ELF signing required)"
    exit 0
fi

echo "❌ muscle failed --version and --help (exit codes: $ret, $ret2)"
cat "$ERR_FILE" 2>/dev/null
exit 1
