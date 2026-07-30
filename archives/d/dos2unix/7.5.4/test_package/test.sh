#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for dos2unix executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

# OHOS: /tmp is read-only (E002), use TMPDIR instead
TMPDIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPDIR"

echo "[test] dos2unix --version"
dos2unix --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    dos2unix --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ dos2unix failed both --version and --help"
        exit 1
    }
}

echo "[test] unix2dos --version"
unix2dos --version && echo "✅ --version OK" || {
    echo "❌ unix2dos --version failed"
    exit 1
}

echo "[test] dos2unix functional test"
# Create a DOS-format file (CRLF line endings)
printf 'hello\r\nworld\r\n' > "$TMPDIR/d2u_test_dos.txt"
# Convert to Unix format (LF)
dos2unix -n "$TMPDIR/d2u_test_dos.txt" "$TMPDIR/d2u_test_unix.txt"
# Verify no CR remains
if grep -q $'\r' "$TMPDIR/d2u_test_unix.txt"; then
    echo "❌ dos2unix conversion failed: CR still present"
    exit 1
fi
echo "✅ dos2unix conversion OK"
rm -f "$TMPDIR/d2u_test_dos.txt" "$TMPDIR/d2u_test_unix.txt"
