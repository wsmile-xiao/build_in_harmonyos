#!/bin/sh
# test_package/test_moon_buggy.sh — verify the packaged moon-buggy binary.
# Invoked by conanfile.py test() through CONFIG_SHELL bash (R5: OHOS has no
# /bin/sh, so the shebang above is informational only — bash sources this file).
#
# Usage: test_moon_buggy.sh <path-to-binary> <expected-version>
#
# Mirrors the upstream Homebrew formula test:
#   assert_match(/Moon-Buggy #{version}$/, shell_output("#{bin}/moon-buggy -V"))
set -eu
set -o pipefail

bin="$1"
expected_version="$2"

# `moon-buggy -V` prints "Moon-Buggy <version>" (e.g. "Moon-Buggy 1.1.0")
# to stdout and exits 0 without initialising curses, so it is safe to run
# in a non-interactive CI environment.
output=$("$bin" -V)
version_line=$(printf '%s\n' "$output" | sed -n '1p')

# Assertion 1: exit code is 0 (set -e handles this implicitly — any non-zero
# exit aborts the script before the next assertion).
# Assertion 2: version string matches the expected value.
expected="Moon-Buggy ${expected_version}"
if [ "$version_line" != "$expected" ]; then
    echo "FAIL: version mismatch" >&2
    echo "  expected: ${expected}" >&2
    echo "  got:      ${version_line}" >&2
    exit 1
fi

echo "PASS: ${version_line}"
