#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for nkf executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] nkf --version"
nkf --version && echo "        [ok] --version" || {
    echo "        [fail] nkf --version failed"
    exit 1
}

echo "[step] nkf encoding conversion (SJIS to UTF-8)"
# Test: convert a simple Shift_JIS string to UTF-8
# "\x82\xb1\x82\xf1\x82\xc9\x82\xbf\x82\xcd" = こんにちは in Shift_JIS
# UTF-8 encoding of こんにちは = e38193e38293e381abe381a1e381af
output=$(printf '\x82\xb1\x82\xf1\x82\xc9\x82\xbf\x82\xcd' | nkf -w | xxd -p | tr -d '\n')
if [ "$output" = "e38193e38293e381abe381a1e381af" ]; then
    echo "        [ok] SJIS to UTF-8 conversion"
else
    echo "        [fail] unexpected output: $output"
    exit 1
fi

echo "[step] nkf UTF-8 passthrough"
echo "hello" | nkf -w | grep -q "hello" && echo "        [ok] passthrough" || {
    echo "        [fail] nkf passthrough failed"
    exit 1
}
