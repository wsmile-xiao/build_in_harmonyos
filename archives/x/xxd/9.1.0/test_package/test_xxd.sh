#!/bin/bash
# test_package/test_xxd.sh – smoke test for xxd binary
# Verifies xxd produces correct hex dump output for known inputs.
# Called by conanfile.py test() method.
set -euo pipefail

XXD_BIN="${XXD_BIN:-xxd}"

echo "[test] Verifying xxd binary exists"
if [ ! -f "$XXD_BIN" ]; then
    echo "FAIL: xxd binary not found at $XXD_BIN"
    exit 1
fi
echo "PASS: xxd binary found"

echo "[test] Running xxd -v (version check)"
output=$("$XXD_BIN" -v 2>&1) || true
case "$output" in
    *"xxd"*|*"Juergen Weigert"*)
        echo "PASS: -v output contains version string"
        ;;
    *)
        echo "FAIL: -v output unexpected: $output"
        exit 1
        ;;
esac

echo "[test] Hex dump of 'hello'"
# xxd default output: offset, hex bytes (grouped in pairs), ASCII representation
# Spacing varies by version; verify hex bytes and ASCII text are correct
output=$(printf "hello" | "$XXD_BIN" 2>/dev/null)
case "$output" in
    *"6865 6c6c 6f"*"hello")
        echo "PASS: hex dump of 'hello' matches expected output"
        ;;
    *)
        echo "FAIL: hex dump mismatch"
        echo "  got: $output"
        exit 1
        ;;
esac

echo "[test] Postscript plain hexdump (-ps)"
output=$(printf "hello" | "$XXD_BIN" -ps 2>/dev/null)
expected="68656c6c6f"
if [ "$output" = "$expected" ]; then
    echo "PASS: -ps output matches expected"
else
    echo "FAIL: -ps mismatch: got '$output', expected '$expected'"
    exit 1
fi

echo "[test] C include output (-i)"
output=$(printf "hello" | "$XXD_BIN" -i 2>/dev/null)
case "$output" in
    *"0x68, 0x65, 0x6c, 0x6c, 0x6f"*)
        echo "PASS: -i output contains C-style hex array"
        ;;
    *)
        echo "FAIL: -i output unexpected: $output"
        exit 1
        ;;
esac

echo "[test] Reverse operation (-r)"
# Round-trip: dump to hex, then reverse back to binary
original="hello world"
dumped=$(printf "$original" | "$XXD_BIN" -ps 2>/dev/null)
reversed=$(printf "$dumped" | "$XXD_BIN" -r -ps 2>/dev/null)
if [ "$reversed" = "$original" ]; then
    echo "PASS: reverse operation (-r -ps) round-trip successful"
else
    echo "FAIL: reverse mismatch: got '$reversed', expected '$original'"
    exit 1
fi

echo "[test] All smoke tests passed"
