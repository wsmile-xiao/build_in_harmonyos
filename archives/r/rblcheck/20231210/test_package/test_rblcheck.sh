#!/bin/sh
# rblcheck 20231210 consumer smoke test.
#
# CONSUMER verification only.  The three upstream automake tests
# (tests/clearlist, tests/addlisting, tests/removelisting) are run by the
# recipe's build() via `make check` — see ../../test_package/MANIFEST.yml.
# Nothing here is counted as an upstream test.
#
# Everything asserted below is local and deterministic.  No DNSBL is contacted:
# `-l` prints the configured zone list and exits before any address is checked.
#
# Requires only POSIX sh + printf/grep.
set -e

if [ $# -lt 1 ]; then
    echo "usage: test_rblcheck.sh <package_bin_dir>" >&2
    exit 2
fi
BIN="$1"
R="$BIN/rblcheck"

# --- 1: packaged binary exists and is executable -----------------------------
[ -x "$R" ] || { echo "rblcheck binary not found/executable: $R" >&2; exit 1; }

tmp="${TMPDIR:-/tmp}/rblcheck_smoke.$$"
rm -rf "$tmp"
mkdir -p "$tmp"
trap 'rm -rf "$tmp"' EXIT

# --- 2/3: -v reports the version and exits 0 --------------------------------
"$R" -v > "$tmp/v.out" 2>&1
grep -q '20231210' "$tmp/v.out" || {
    echo "-v did not report 20231210:" >&2; cat "$tmp/v.out" >&2; exit 1; }

# --- 4: -h prints usage and exits 0 -----------------------------------------
"$R" -h > "$tmp/h.out" 2>&1
grep -qi 'usage' "$tmp/h.out" || {
    echo "-h did not print usage:" >&2; cat "$tmp/h.out" >&2; exit 1; }

# --- 5: no arguments is an error --------------------------------------------
rc=0
"$R" >/dev/null 2>&1 || rc=$?
[ "$rc" -ne 0 ] || { echo "rblcheck with no arguments exited 0" >&2; exit 1; }

# --- 6: clearing the zone list yields an empty listing ----------------------
out=$("$R" -c -l 2>&1)
[ -z "$out" ] || {
    echo "-c -l should be empty but printed:" >&2; printf '%s\n' "$out" >&2; exit 1; }

# --- 7: adding a zone makes it appear in the listing ------------------------
out=$("$R" -c -s testlisting -l 2>&1 | grep -v '^#' | uniq)
[ "$out" = "testlisting" ] || {
    echo "-c -s testlisting -l gave '$out', expected 'testlisting'" >&2; exit 1; }

# --- 8: toggling the same zone twice removes it -----------------------------
out=$("$R" -c -s testlisting -s testlisting -l 2>&1)
[ -z "$out" ] || {
    echo "double toggle should be empty but printed:" >&2; printf '%s\n' "$out" >&2; exit 1; }

# --- 9: clear after add also empties the list -------------------------------
out=$("$R" -c -s testlisting -c -l 2>&1)
[ -z "$out" ] || {
    echo "-c after -s should be empty but printed:" >&2; printf '%s\n' "$out" >&2; exit 1; }

# --- 10: a real query runs to completion without crashing -------------------
# 127.0.0.1 against the reserved, guaranteed-non-resolving ".invalid" TLD: the
# resolver is exercised, the answer is "not listed", and the process must exit
# cleanly rather than abort.  No external service is depended upon.
"$R" -s test.invalid 127.0.0.1 > "$tmp/q.out" 2>&1 && qrc=0 || qrc=$?
[ "$qrc" -lt 126 ] || {
    echo "querying .invalid crashed or was killed (exit $qrc):" >&2
    cat "$tmp/q.out" >&2
    exit 1; }

echo "rblcheck smoke test OK (version/help/no-args/zone-list/toggle/query)"
