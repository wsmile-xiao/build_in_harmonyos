#!/usr/bin/env bash
# test_package/test.sh — consumer smoke test for aiac executable
# Asserts: (1) --version reports v5.3.0; (2-3) --help lists core flags;
#          (4) missing-backend error path fails closed with a diagnostic.
set -euo pipefail

# HMBS injects TMPDIR/TMP/TEMP; cd there so the shell is not left in an HMDFS
# cwd that breaks getcwd (`[shell_getcwd]` diagnostic).
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}" 2>/dev/null || cd /tmp 2>/dev/null || true

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-aiac>" >&2
    exit 2
fi

aiac_bin="$1"

if [ ! -f "$aiac_bin" ]; then
    echo "aiac binary not found: $aiac_bin" >&2
    exit 1
fi

echo "[step] Testing aiac --version..."
version_output="$("$aiac_bin" --version 2>&1)"
echo "version output: $version_output"
printf '%s\n' "$version_output" | grep -F "aiac version v5.3.0" >/dev/null
echo "        [ok] version check passed"

echo "[step] Testing aiac --help..."
help_output="$("$aiac_bin" --help 2>&1)"
printf '%s\n' "$help_output" | grep -F "list-models" >/dev/null
printf '%s\n' "$help_output" | grep -F "backend" >/dev/null
echo "        [ok] help check passed"

echo "[step] Testing aiac --list-models with a config that has no default backend..."
test_dir="${TMPDIR:-${TMP:-${TEMP:-/tmp}}}/aiac-test-$$"
rm -rf "$test_dir"
mkdir -p "$test_dir/aiac"
printf '[backends]\n' > "$test_dir/aiac/aiac.toml"
set +e
XDG_CONFIG_HOME="$test_dir" "$aiac_bin" --list-models > "$test_dir/list.out" 2>&1
list_rc=$?
set -e
echo "list-models exit code: $list_rc"
cat "$test_dir/list.out"
[ "$list_rc" -ne 0 ]
grep -qE "backend not selected|Failed listing models|no default" "$test_dir/list.out"
rm -rf "$test_dir"
echo "        [ok] missing-backend error path passed"

echo "[ok] All tests passed."
