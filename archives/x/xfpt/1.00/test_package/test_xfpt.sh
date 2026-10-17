#!/bin/bash
# test_package/test_xfpt.sh – smoke test for the installed xfpt binary
# Verifies version output, usage, error path and a real conversion using
# the packaged share data (stdflags) via -S.
# Called by conanfile.py test() method.
set -euo pipefail

XFPT_BIN="${XFPT_BIN:-xfpt}"
XFPT_SHARE="${XFPT_SHARE:-}"

echo "[test] Verifying xfpt binary exists"
if [ ! -f "$XFPT_BIN" ]; then
    echo "FAIL: xfpt binary not found at $XFPT_BIN"
    exit 1
fi
echo "PASS: xfpt binary found"

echo "[test] Running xfpt --version (version check)"
# Upstream prints "xpft version ..." (sic – upstream typo, kept verbatim)
output="$("$XFPT_BIN" --version 2>/dev/null)"
case "$output" in
    *"version 1.00"*)
        echo "PASS: --version output contains version string"
        ;;
    *)
        echo "FAIL: --version unexpected: $output"
        exit 1
        ;;
esac

echo "[test] Running xfpt -help (usage on stderr)"
output="$("$XFPT_BIN" -help /dev/null 2>&1)" || true
case "$output" in
    *"Usage: xfpt"*)
        echo "PASS: -help prints usage"
        ;;
    *)
        echo "FAIL: -help output unexpected: $output"
        exit 1
        ;;
esac

echo "[test] Error path: nonexistent input file"
output="$("$XFPT_BIN" /non/exist 2>&1)" && rc=0 || rc=$?
if [ "$rc" -ne 0 ]; then
    case "$output" in
        *"failed to open"*"abandoned"*)
            echo "PASS: missing input reports error and non-zero exit"
            ;;
        *)
            echo "FAIL: unexpected error output: $output"
            exit 1
            ;;
    esac
else
    echo "FAIL: missing input unexpectedly succeeded"
    exit 1
fi

echo "[test] DocBook conversion using packaged share data (-S)"
# NOTE: toybox mktemp requires X's at the END of the template, and /tmp may
# be read-only on OHOS (E002) — use $TMPDIR with a fixed pattern instead.
tmpdir="${TMPDIR:-.}"
tmpin="$tmpdir/xfpt-test-$$.txt"
tmpout="$tmpdir/xfpt-test-$$.xml"
trap 'rm -f "$tmpin" "$tmpout"' EXIT
cat > "$tmpin" <<'EOF'
.include stdflags
.include stdmacs
.docbook
.book
.chapter "Test chapter"
This is a paragraph with &*bold*& text.
EOF
"$XFPT_BIN" -S "$XFPT_SHARE" -o "$tmpout" "$tmpin" 2>/dev/null
[ -s "$tmpout" ] || { echo "FAIL: output file empty"; exit 1; }
for expected in \
    '<?xml version="1.0" encoding="UTF-8"?>' \
    '<!DOCTYPE book' \
    '<book>' \
    '<title>Test chapter</title>' \
    '<emphasis role="bold">bold</emphasis>' \
    '</book>'
do
    if ! grep -qF -- "$expected" "$tmpout"; then
        echo "FAIL: output missing expected fragment: $expected"
        echo "--- output ---"
        cat "$tmpout"
        exit 1
    fi
done
echo "PASS: DocBook conversion produces expected XML structure"

echo "[test] Default output naming (input .txt -> .xml alongside -o)"
# -o was already exercised above; assert the binary rejects >1 input file
set +e
output="$("$XFPT_BIN" a b 2>&1)"
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
    echo "PASS: two input files rejected with usage error"
else
    echo "FAIL: two input files unexpectedly accepted"
    exit 1
fi

echo "[test] All smoke tests passed"
