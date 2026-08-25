#!/data/service/hnp/bin/bash
# test_package/test.sh — functional test for cd-discid executable
# cd-discid reads the TOC of a real CD-ROM via ioctl; no CD-ROM device is
# available in the OHOS build/CI sandbox, so we verify the binary's actual
# runtime behavior on the open/usage/argument-handling paths instead:
#   - binary is present and executable
#   - too many args  -> prints Usage: and exits non-zero
#   - bad device arg -> prints open() error, exits non-zero
#   - no args        -> defaults to /dev/cdrom, prints open() error, exits non-zero
set -euo pipefail

echo "[test] cd-discid: locate binary"
BIN="$(command -v cd-discid || true)"
if [ -z "$BIN" ]; then
    echo "FAIL: cd-discid not found on PATH"
    exit 1
fi
echo "OK: binary at $BIN"
[ -x "$BIN" ] || { echo "FAIL: $BIN not executable"; exit 1; }

echo "[test] cd-discid: too many args -> usage message + non-zero exit"
set +e
OUT="$("$BIN" a b c 2>&1)"
RC=$?
set -e
echo "  exit=$RC"
if [ "$RC" -eq 0 ]; then
    echo "FAIL: expected non-zero exit for bad args"
    exit 1
fi
if ! echo "$OUT" | grep -q "Usage:" || ! echo "$OUT" | grep -q "cd-discid"; then
    echo "FAIL: expected 'Usage:' message mentioning cd-discid, got: $OUT"
    exit 1
fi
echo "OK: usage message emitted"

echo "[test] cd-discid: nonexistent device -> open error + non-zero exit"
set +e
OUT="$("$BIN" /dev/nonexistent-cdrom 2>&1)"
RC=$?
set -e
echo "  exit=$RC"
if [ "$RC" -eq 0 ]; then
    echo "FAIL: expected non-zero exit for missing device"
    exit 1
fi
if ! echo "$OUT" | grep -q "No such file or directory"; then
    echo "FAIL: expected open() error message, got: $OUT"
    exit 1
fi
echo "OK: open() error message emitted"

echo "[test] cd-discid: no args -> defaults to /dev/cdrom, open error + non-zero exit"
set +e
OUT="$("$BIN" 2>&1)"
RC=$?
set -e
echo "  exit=$RC"
if [ "$RC" -eq 0 ]; then
    echo "FAIL: expected non-zero exit when no CD-ROM present"
    exit 1
fi
if ! echo "$OUT" | grep -q "/dev/cdrom"; then
    echo "FAIL: expected default device /dev/cdrom in output, got: $OUT"
    exit 1
fi
echo "OK: default device referenced"

echo "PASS: cd-discid runtime behavior verified"
