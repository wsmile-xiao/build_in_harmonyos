#!/usr/bin/env bash
# test_package/test.sh — smoke test for the postsrsd executable
# (invoked as "$CONFIG_SHELL test.sh"; the shebang is a convenience fallback)
set -euo pipefail

echo "[step] postsrsd --version (-v)"
ver=$(postsrsd -v 2>&1 | head -1)
echo "        version output: $ver"
[ "$ver" = "2.0.11" ] || {
    echo "        [fail] unexpected version: '$ver'"
    exit 1
}
echo "        [ok] -v version OK"

echo "[step] postsrsd -h (help)"
tmpdir=${TMPDIR:-${HOME:-/tmp}}
mkdir -p "$tmpdir"
help_out="$tmpdir/postsrsd-help.$$.txt"
postsrsd -h > "$help_out" 2>&1 || {
    echo "        [fail] -h failed"
    exit 1
}
grep -q "PostSRSd" "$help_out" || {
    echo "        [fail] -h output missing 'PostSRSd'"
    cat "$help_out"
    exit 1
}
rm -f "$help_out"
echo "        [ok] -h help OK"