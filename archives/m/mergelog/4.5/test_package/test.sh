#!/bin/sh
# test_package/test.sh — real functional test for the packaged mergelog/zmergelog
#
# Upstream ships no test suite (Makefile `check` is the empty autotools default;
# see MANIFEST.yml for the full evidence). This script fills that gap by running
# the packaged CLI binaries on Common Log Format fixtures and asserting on
# their date-sorted merge output, the no-args usage contract, and the gzip path
# via zmergelog on .gz fixtures (zlib end-to-end).
#
# Conan's conanrun env puts mergelog/zmergelog on PATH and exports zlib's
# runtime library path; this script is invoked from test_package/conanfile.py
# via `self.run("sh <abs path to test.sh>", env="conanrun")`.
#
# OHOS note: /tmp is read-only and the system busybox sh writes its internal
# temp files (for here-docs and $(…) command substitution) to /tmp, ignoring
# TMPDIR. This script therefore avoids here-docs and command substitution
# entirely, keeps all its own temp files inside this (writable) test_package
# directory, and ships the expected output as a fixture (expected.log) instead
# of generating it with a here-doc.
#
# Exit 0 = pass, non-zero = fail (with a diagnostic on stderr).

set -eu

# $0 is the absolute path to this script (conanfile.py passes an abs path via
# `sh <path>`). Derive script_dir with POSIX parameter expansion only — NO
# $(…) command substitution, because the system busybox sh writes the temp
# file for command substitution to read-only /tmp (ignoring TMPDIR). $0 is
# ".../test.sh", so strip the trailing "/test.sh" to get the directory.
case "$0" in
    */*) script_dir=${0%/*} ;;
    *)   script_dir=. ;;
esac
a_log="$script_dir/a.log"
b_log="$script_dir/b.log"
expected_log="$script_dir/expected.log"

# All temp output goes into a writable dir inside test_package (HOME is also
# writable, but keeping test artifacts together is cleaner). Export TMPDIR too
# so any child tool (gzip, cmp) that honors it stays off read-only /tmp.
work="$script_dir/.work"
rm -rf "$work"
mkdir -p "$work"
export TMPDIR="$work"

# Sanity: fixtures must exist.
test -f "$a_log"      || { echo "FAIL: missing fixture $a_log" >&2; exit 1; }
test -f "$b_log"      || { echo "FAIL: missing fixture $b_log" >&2; exit 1; }
test -f "$expected_log" || { echo "FAIL: missing fixture $expected_log" >&2; exit 1; }

# The binaries must be on PATH (conanrun env).
command -v mergelog  >/dev/null 2>&1 || { echo "FAIL: mergelog not on PATH" >&2; exit 1; }
command -v zmergelog >/dev/null 2>&1 || { echo "FAIL: zmergelog not on PATH" >&2; exit 1; }

# cmp compares in-memory (busybox diff hardcodes /tmp, which is read-only on
# OHOS); print a line-by-line diagnostic only when cmp finds a mismatch.
assert_same() {
    label="$1"; exp="$2"; got="$3"
    if cmp -s "$exp" "$got"; then
        return 0
    fi
    echo "FAIL: $label — output mismatch" >&2
    echo "--- expected ---" >&2
    cat "$exp" >&2
    echo "--- actual ---" >&2
    cat "$got" >&2
    return 1
}

# ── Assertion 1: no-args contract (usage to stderr, non-zero exit) ──
if mergelog >/dev/null 2>"$work/usage.err"; then
    echo "FAIL: mergelog with no args should exit non-zero" >&2
    exit 1
fi
test -s "$work/usage.err" || { echo "FAIL: mergelog with no args should print usage to stderr" >&2; exit 1; }

# ── Assertion 2: mergelog merges in ascending timestamp order ──
mergelog "$a_log" "$b_log" > "$work/merged.txt"
assert_same "mergelog order" "$expected_log" "$work/merged.txt"

# ── Assertion 3: zmergelog on plain inputs matches mergelog ──
zmergelog "$a_log" "$b_log" > "$work/zmerged.txt"
assert_same "zmergelog plain vs mergelog" "$work/merged.txt" "$work/zmerged.txt"

# ── Assertion 4: zmergelog on gzip inputs matches mergelog (zlib path) ──
gzip -kc "$a_log" > "$work/a.log.gz"
gzip -kc "$b_log" > "$work/b.log.gz"
zmergelog "$work/a.log.gz" "$work/b.log.gz" > "$work/zmerged_gz.txt"
assert_same "zmergelog gzip vs mergelog" "$work/merged.txt" "$work/zmerged_gz.txt"

rm -rf "$work"
echo "mergelog test_package: all 4 assertions passed"
