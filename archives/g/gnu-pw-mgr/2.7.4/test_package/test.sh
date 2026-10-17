#!/bin/bash
# Consumer test for gnu-pw-mgr binaries, run against the installed package.
# Asserts real behaviour of the sort-pw-cfg utility (config-file validation).
set -e

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# 1. Smoke: sort-pw-cfg --version exits 0.
sort-pw-cfg --version > /dev/null

# 2. Functional: the config parser validates structure — a config file
#    missing the required id tag must be rejected with a specific error.
printf '[sec1]\n  dom = zzz.example.com\n' > "$WORK/bad.cfg"
if sort-pw-cfg "$WORK/bad.cfg" > "$WORK/out.txt" 2>&1; then
    echo "FAIL: sort-pw-cfg accepted a config file without an id tag"
    exit 1
fi
grep -q "missing id tag" "$WORK/out.txt" || {
    echo "FAIL: expected 'missing id tag' diagnostic, got:"
    cat "$WORK/out.txt"
    exit 1
}

echo "gnu-pw-mgr consumer test passed (sort-pw-cfg validation path)"
