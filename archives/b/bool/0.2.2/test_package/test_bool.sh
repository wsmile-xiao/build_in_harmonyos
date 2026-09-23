#!/bin/sh
set -eu

BOOL=${1:?missing bool binary}
test -x "$BOOL"

tmp_dir="${PWD}/bool-test.$$"
trap 'rm -rf "$tmp_dir"' EXIT HUP INT TERM
mkdir "$tmp_dir"

version="$($BOOL --version)"
printf '%s\n' "$version" | grep -Fq "bool (GNU)"
printf '%s\n' "$version" | grep -Fq "0.2.2"

if printf '%s\n' 'a b c' | "$BOOL" 'a AND c' > "$tmp_dir/match"; then
    grep -Fqx 'a:a b c' "$tmp_dir/match"
    grep -Fqx 'c:a b c' "$tmp_dir/match"
else
    echo 'boolean match unexpectedly failed' >&2
    exit 1
fi

if printf '%s\n' 'a b c' | "$BOOL" 'a AND z' > "$tmp_dir/no-match"; then
    echo 'boolean non-match unexpectedly succeeded' >&2
    exit 1
else
    rc=$?
    test "$rc" -eq 1
fi

if printf '%s\n' 'alpha beta' | "$BOOL" -F 'alpha' > "$tmp_dir/fixed"; then
    grep -Fqx 'alpha beta' "$tmp_dir/fixed"
else
    echo 'fixed-string match unexpectedly failed' >&2
    exit 1
fi

if "$BOOL" 'alpha' "$tmp_dir/no-such-file" > /dev/null 2>&1; then
    echo 'missing-file invocation unexpectedly succeeded' >&2
    exit 1
else
    rc=$?
    test "$rc" -eq 1
fi
