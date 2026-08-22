#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for basez CLI binary
# Uses RFC 4648 Section 10 test vectors to verify encode/decode.
# Runs in conanrun env (PATH includes installed bin/).
set -eu

BASEZ="$1"
FAIL=0

# basez encoding selection:
#   When invoked as 'basez': defaults to base64
#   --base16 / -b16: base16
#   --base32 / -b32: base32
#   --base64 / -a:   base64 (default)
# Encode/decode mode:
#   No flag: defaults to encode
#   -d / --decode: decode mode
# Note: -e selects base32hex encoding, NOT encode mode!

assert_encode() {
    local label="$1" input="$2" expected="$3"
    local got
    got=$(printf '%s' "$input" | "$BASEZ" 2>/dev/null | tr -d '\n')
    if [ "$got" = "$expected" ]; then
        echo "PASS: $label encode: '$input' -> '$got'"
    else
        echo "FAIL: $label encode: expected '$expected', got '$got'"
        FAIL=1
    fi
}

assert_decode() {
    local label="$1" input="$2" expected="$3"
    local got
    got=$(printf '%s' "$input" | "$BASEZ" -d 2>/dev/null | tr -d '\n')
    if [ "$got" = "$expected" ]; then
        echo "PASS: $label decode: '$input' -> '$got'"
    else
        echo "FAIL: $label decode: expected '$expected', got '$got'"
        FAIL=1
    fi
}

assert_encode_flag() {
    local label="$1" flag="$2" input="$3" expected="$4"
    local got
    got=$(printf '%s' "$input" | "$BASEZ" "$flag" 2>/dev/null | tr -d '\n')
    if [ "$got" = "$expected" ]; then
        echo "PASS: $label encode: '$input' -> '$got'"
    else
        echo "FAIL: $label encode: expected '$expected', got '$got'"
        FAIL=1
    fi
}

echo "[test] basez version/help"
"$BASEZ" --version 2>/dev/null && echo "PASS: --version OK" || {
    "$BASEZ" -h > /dev/null 2>&1 && echo "PASS: -h OK" || {
        echo "WARN: version/help check skipped"
    }
}

# RFC 4648 Section 10 test vectors — base64 (default when invoked as 'basez')
echo "[test] base64 encoding (RFC 4648, default mode)"
assert_encode  "base64" "f"       "Zg=="
assert_encode  "base64" "fo"      "Zm8="
assert_encode  "base64" "foo"     "Zm9v"
assert_encode  "base64" "foob"    "Zm9vYg=="
assert_encode  "base64" "fooba"   "Zm9vYmE="
assert_encode  "base64" "foobar"  "Zm9vYmFy"

# base64 decode
assert_decode  "base64" "Zm9vYmFy" "foobar"
assert_decode  "base64" "Zg=="     "f"

# RFC 4648 test vectors — base16 (via --base16 flag)
echo "[test] base16 encoding (RFC 4648, via --base16)"
assert_encode_flag "base16" "--base16" "f"      "66"
assert_encode_flag "base16" "--base16" "fo"     "666f"
assert_encode_flag "base16" "--base16" "foobar" "666f6f626172"

# RFC 4648 test vectors — base32 (via --base32 flag)
echo "[test] base32 encoding (RFC 4648, via --base32)"
assert_encode_flag "base32" "--base32" "f"      "MY======"
assert_encode_flag "base32" "--base32" "fo"     "MZXQ===="
assert_encode_flag "base32" "--base32" "foobar" "MZXW6YTBOI======"

echo ""
if [ "$FAIL" -eq 0 ]; then
    echo "All basez tests PASSED"
else
    echo "Some basez tests FAILED"
    exit 1
fi
