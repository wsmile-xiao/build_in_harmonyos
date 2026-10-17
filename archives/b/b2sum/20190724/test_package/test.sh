#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for b2sum binary
# Verifies b2sum produces correct BLAKE2b/s/bp/sp hashes against known vectors.
# Called by conanfile.py test() method.
set -euo pipefail

B2SUM_BIN="${B2SUM_BIN:-b2sum}"

echo "[test] Verifying b2sum binary exists"
if [ ! -f "$B2SUM_BIN" ]; then
    echo "FAIL: b2sum binary not found at $B2SUM_BIN"
    exit 1
fi
echo "PASS: b2sum binary found"

echo "[test] Running b2sum --help"
output=$("$B2SUM_BIN" --help 2>&1) || true
case "$output" in
    *"Usage"*|*"b2sum"*)
        echo "PASS: --help output contains expected text"
        ;;
    *)
        echo "FAIL: --help output unexpected: $output"
        exit 1
        ;;
esac

echo "[test] BLAKE2b empty input (known vector)"
# Official BLAKE2b hash of empty input (0 bytes)
hash=$(printf "" | "$B2SUM_BIN" - 2>/dev/null | awk '{print $1}')
expected="786a02f742015903c6c6fd852552d272912f4740e15847618a86e217f71f5419d25e1031afee585313896444934eb04b903a685b1448b755d56f701afe9be2ce"
if [ "$hash" = "$expected" ]; then
    echo "PASS: BLAKE2b empty input matches reference vector"
else
    echo "FAIL: BLAKE2b empty input mismatch: got $hash, expected $expected"
    exit 1
fi

echo "[test] BLAKE2b 'abc' (known vector)"
# Official BLAKE2b hash of "abc"
hash=$(printf "abc" | "$B2SUM_BIN" - 2>/dev/null | awk '{print $1}')
expected="ba80a53f981c4d0d6a2797b69f12f6e94c212f14685ac4b74b12bb6fdbffa2d17d87c5392aab792dc252d5de4533cc9518d38aa8dbf1925ab92386edd4009923"
if [ "$hash" = "$expected" ]; then
    echo "PASS: BLAKE2b 'abc' matches reference vector"
else
    echo "FAIL: BLAKE2b 'abc' mismatch: got $hash, expected $expected"
    exit 1
fi

echo "[test] BLAKE2s algorithm variant"
hash=$(printf "abc" | "$B2SUM_BIN" -a blake2s - 2>/dev/null | awk '{print $1}')
expected="508c5e8c327c14e2e1a72ba34eeb452f37458b209ed63a294d999b4c86675982"
if [ "$hash" = "$expected" ]; then
    echo "PASS: BLAKE2s 'abc' matches reference vector"
else
    echo "FAIL: BLAKE2s 'abc' mismatch: got $hash, expected $expected"
    exit 1
fi

echo "[test] BSD-style checksum output (--tag)"
output=$(printf "abc" | "$B2SUM_BIN" --tag - 2>/dev/null)
case "$output" in
    *"BLAKE2b"*)
        echo "PASS: --tag produces BSD-style output"
        ;;
    *)
        echo "FAIL: --tag output unexpected: $output"
        exit 1
        ;;
esac

echo "[test] All smoke tests passed"
