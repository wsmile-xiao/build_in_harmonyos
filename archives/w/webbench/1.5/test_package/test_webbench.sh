#!/usr/bin/env bash
# webbench 1.5 consumer smoke test.
#
# Covers the POSIX surface webbench actually uses on the target platform:
# usage/version paths, the connect-failure path, and a REAL benchmark against a
# local HTTP server bound to 127.0.0.1 — no public-internet dependency, so the
# result does not depend on external site availability.
#
# UPSTREAM QUIRK (documented, not worked around): `bench()` ends with
# `return i;` where `i` is the last value parsed by
# `fscanf(f,"%d %d %d",&i,&j,&k)` — i.e. the last child's page count, not a
# status.  A *successful* benchmark therefore exits with an arbitrary 0-255
# value (observed 223).  The exit code is only meaningful for the pre-benchmark
# paths (-V / usage / connect failure).  This test asserts on the benchmark's
# stdout report instead, and asserts exit codes only where upstream defines them.
#
# Requires bash, a python3 with http.server (used as the local target), plus
# printf/grep/sed/tar/mktemp.
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: test_webbench.sh <package_bin_dir>" >&2
    exit 2
fi
BIN="$1"
W="$BIN/webbench"

# --- 1: packaged binary exists and is executable -----------------------------
[ -x "$W" ] || { echo "webbench binary not found/executable: $W" >&2; exit 1; }

# Unpredictable scratch dir (the previous `webbench_smoke.$$` was guessable).
tmp=$(mktemp -d "${TMPDIR:-/tmp}/webbench_smoke.XXXXXXXX") || {
    echo "cannot create a scratch dir under ${TMPDIR:-/tmp}" >&2; exit 1; }
mkdir -p "$tmp/www"
printf 'webbench local test payload\n' > "$tmp/www/index.html"

HTTPD_PID=""
# Kill the server, then remove the scratch dir — unconditionally.  Written as an
# explicit `if` rather than `[ -n "$x" ] && kill`: under `set -e` the && form
# returns non-zero when the variable is empty, which would abort the trap before
# the `rm -rf` ran and leak the directory.
cleanup() {
    if [ -n "$HTTPD_PID" ]; then
        kill "$HTTPD_PID" 2>/dev/null || true
    fi
    rm -rf "$tmp"
}
trap cleanup EXIT INT TERM

# --- 2/3: version flag prints 1.5 and exits 0 --------------------------------
"$W" -V > "$tmp/v.out" 2>&1
grep -q '^1\.5' "$tmp/v.out" || {
    echo "webbench -V did not print 1.5:" >&2; cat "$tmp/v.out" >&2; exit 1; }

# --- 4: no arguments -> usage on stderr, exit 2 ------------------------------
if "$W" >/dev/null 2>&1; then
    echo "webbench with no arguments should have exited non-zero" >&2; exit 1
fi
rc=0
"$W" > "$tmp/u.out" 2>&1 || rc=$?
[ "$rc" = "2" ] || { echo "no-args exit $rc != 2" >&2; exit 1; }
grep -q 'webbench \[option\]' "$tmp/u.out" || {
    echo "no-args did not print usage:" >&2; cat "$tmp/u.out" >&2; exit 1; }

# --- 5: --help exits 2 (upstream returns 2, not 0) ---------------------------
rc=0
"$W" --help >/dev/null 2>&1 || rc=$?
[ "$rc" = "2" ] || { echo "--help exit $rc != 2" >&2; exit 1; }

# --- 6: connect failure path exits 1 -----------------------------------------
rc=0
"$W" -t 1 -c 1 "http://127.0.0.1:9/" >/dev/null 2>&1 || rc=$?
[ "$rc" = "1" ] || { echo "connect-failure exit $rc != 1" >&2; exit 1; }

# --- 7: start a local HTTP server (127.0.0.1 only, ephemeral port) -----------
# `-u` is required: python block-buffers stdout when redirected to a file, so
# without it the "Serving HTTP ... port N" line never reaches the log and the
# port cannot be discovered.  We cd into the docroot instead of using
# --directory so this works on any Python 3 (--directory needs >= 3.7).
( cd "$tmp/www" && exec python3 -u -m http.server --bind 127.0.0.1 0 ) \
    > "$tmp/httpd.log" 2>&1 &
HTTPD_PID=$!

# `sed -n '1p'` (rather than `head -n 1`) drains its input, so the upstream sed
# never takes SIGPIPE — which matters under `set -o pipefail`.
PORT=""
n=0
while [ "$n" -lt 30 ]; do
    PORT=$(sed -n 's/.*port \([0-9][0-9]*\).*/\1/p' "$tmp/httpd.log" | sed -n '1p')
    if [ -n "$PORT" ]; then
        break
    fi
    n=$((n + 1))
    sleep 1
done
[ -n "$PORT" ] || {
    echo "local HTTP server did not report a port" >&2
    cat "$tmp/httpd.log" >&2
    exit 1
}
kill -0 "$HTTPD_PID" 2>/dev/null || {
    echo "local HTTP server died" >&2; cat "$tmp/httpd.log" >&2; exit 1; }

# --- 8: real benchmark against 127.0.0.1 ------------------------------------
"$W" -t 2 -c 2 "http://127.0.0.1:$PORT/index.html" > "$tmp/bench.out" 2>&1 || true
cat "$tmp/bench.out"

# --- 9: report contains a Speed line ----------------------------------------
grep -q 'Speed=' "$tmp/bench.out" || {
    echo "benchmark produced no Speed= report" >&2; exit 1; }

# --- 10: report contains a Requests line ------------------------------------
grep -q 'susceed' "$tmp/bench.out" || {
    echo "benchmark produced no Requests line" >&2; exit 1; }

# --- 11: the benchmark REALLY did work --------------------------------------
# A `Speed=0 ... Requests: 0 susceed, 0 failed` run is NOT a pass: it is what
# OHOS produced before the _IONBF fix, because the parent could not parse its
# children's results.  Require a strictly positive number of served requests.
served=$(sed -n 's/.*Requests: \([0-9][0-9]*\) susceed.*/\1/p' "$tmp/bench.out" | sed -n '1p')
[ -n "$served" ] || {
    echo "could not parse the served-request count:" >&2
    cat "$tmp/bench.out" >&2
    exit 1; }
[ "$served" -gt 0 ] || {
    echo "benchmark completed ZERO successful requests against a healthy local server" >&2
    cat "$tmp/bench.out" >&2
    exit 1; }

# --- 12: no failed requests -------------------------------------------------
failed=$(sed -n 's/.* \([0-9][0-9]*\) failed.*/\1/p' "$tmp/bench.out" | sed -n '1p')
[ "$failed" = "0" ] || {
    echo "benchmark reported $failed failed requests against a healthy local server" >&2
    cat "$tmp/bench.out" >&2
    exit 1; }

# --- 13: the parent did not lose its worker processes -----------------------
if grep -q 'childrens died' "$tmp/bench.out"; then
    echo "benchmark reported 'Some of our childrens died.'" >&2
    cat "$tmp/bench.out" >&2
    exit 1
fi

echo "webbench smoke test OK (version/usage/connect-failure/local-benchmark: $served requests served, 0 failed)"
