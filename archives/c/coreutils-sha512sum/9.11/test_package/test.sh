#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the package's own sha512sum executable
# Usage: test.sh <absolute-path-to-package-sha512sum>
# R34/L1e: all invocations use the package binary explicitly ($1), never PATH,
# so the destructive negative test (bin/ moved away) correctly FAILS when the
# test no longer depends on the package artifact.
set -eu

BIN="$1"
[ -x "$BIN" ] || { echo "binary not executable: $BIN"; exit 1; }

echo "[test] $BIN --version"
"$BIN" --version | head -1
echo "✅ --version OK"

echo "[test] sha512sum of known string 'abc'"
# SHA-512("abc") = ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f
out=$(printf 'abc' | "$BIN" | awk '{print $1}')
echo "got: $out"
[ "$out" = "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f" ] || {
    echo "[test] known-vector digest mismatch"
    exit 1
}
echo "✅ known-vector digest OK"

echo "[test] sha512sum -c check mode"
printf 'hello harmonyos\n' > sample.txt
printf '%s  sample.txt\n' "$("$BIN" sample.txt | awk '{print $1}')" > sample.txt.sha512
"$BIN" -c sample.txt.sha512
echo "✅ -c check mode OK"

echo "[test] sha512sum file mode + stdin consistency"
file_digest=$("$BIN" sample.txt | awk '{print $1}')
stdin_digest=$(cat sample.txt | "$BIN" | awk '{print $1}')
[ "$file_digest" = "$stdin_digest" ] || {
    echo "[test] file/stdin digest mismatch"
    exit 1
}
echo "✅ file/stdin consistency OK"

rm -f sample.txt sample.txt.sha512
echo "All tests passed ✅"
