#!/bin/sh
# pipebench smoke test from a consumer point of view.
# pipebench copies stdin to stdout while measuring throughput, so a full test is:
#   - `-h` prints usage and exits 0
#   - feeding bytes through `-q` reproduces them byte-for-byte (cmp)
#   - stderr contains the Summary line (rate in ...B/second)
# Only POSIX sh + pipebench + printf/cat/cmp/grep are required.
set -e

if [ $# -lt 1 ]; then
    echo "usage: test_pipebench.sh <package_bin_dir>" >&2
    exit 2
fi
BIN="$1"
P="$BIN/pipebench"

[ -x "$P" ] || { echo "pipebench binary not found/executable: $P" >&2; exit 1; }

# usage screen must exit 0
"$P" -h >/dev/null 2>&1 || { echo "pipebench -h failed" >&2; exit 1; }

tmp="${TMPDIR:-/tmp}/pipebench_smoke.$$"
rm -rf "$tmp"
mkdir -p "$tmp"
trap 'rm -rf "$tmp"' EXIT

# ~6.2 KB of mixed alnum/newline data, big enough to cross multiple fread/fwrite
i=0
: > "$tmp/in"
while [ "$i" -lt 100 ]; do
    printf '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ\n'
    i=$((i + 1))
done > "$tmp/in"
[ -s "$tmp/in" ] || { echo "failed to build test input" >&2; exit 1; }

# -q quiet mode: suppress per-second updates, keep the final Summary on stderr
"$P" -q < "$tmp/in" > "$tmp/out" 2> "$tmp/stats" || {
    echo "pipebench -q failed" >&2; cat "$tmp/stats" >&2; exit 1; }

cmp -s "$tmp/in" "$tmp/out" || { echo "pipebench output mismatch (bytes not preserved)" >&2; exit 1; }

grep -q 'B/second' "$tmp/stats" || {
    echo "pipebench Summary not found on stderr; got:" >&2; cat "$tmp/stats" >&2; exit 1; }

echo "pipebench smoke test OK"
