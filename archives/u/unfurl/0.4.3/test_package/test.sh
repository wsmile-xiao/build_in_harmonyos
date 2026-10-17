#!/usr/bin/env bash
set -euo pipefail

# HMBS injects TMPDIR/TMP/TEMP; cd there first so the shell is not left
# in an HMDFS cwd that breaks getcwd (`[shell_getcwd]` diagnostic).
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}" 2>/dev/null || cd /tmp 2>/dev/null || true

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-unfurl>" >&2
    exit 2
fi

unfurl_bin="$1"

if [ ! -f "$unfurl_bin" ]; then
    echo "unfurl binary not found: $unfurl_bin" >&2
    exit 1
fi

echo "[step] Testing unfurl domains mode..."
domains_output="$(printf 'https://sub.example.com/users?id=123&name=Sam\n' | "$unfurl_bin" domains 2>&1)"
echo "domains output: $domains_output"
printf '%s\n' "$domains_output" | grep -F "sub.example.com" >/dev/null
echo "        [ok] domains check passed"

echo "[step] Testing unfurl paths mode..."
paths_output="$(printf 'https://sub.example.com/users?id=123&name=Sam\n' | "$unfurl_bin" paths 2>&1)"
echo "paths output: $paths_output"
printf '%s\n' "$paths_output" | grep -F "/users" >/dev/null
echo "        [ok] paths check passed"

echo "[step] Testing unfurl keys mode..."
keys_output="$(printf 'https://sub.example.com/users?id=123&name=Sam\n' | "$unfurl_bin" keys 2>&1)"
echo "keys output: $keys_output"
printf '%s\n' "$keys_output" | grep -F "id" >/dev/null
printf '%s\n' "$keys_output" | grep -F "name" >/dev/null
echo "        [ok] keys check passed"

echo "[step] Testing unfurl format mode..."
format_output="$(printf 'https://sub.example.com/users?id=123&name=Sam\n' | "$unfurl_bin" format '%d%p' 2>&1)"
echo "format output: $format_output"
printf '%s\n' "$format_output" | grep -F "sub.example.com/users" >/dev/null
echo "        [ok] format check passed"

echo "[ok] All tests passed."
