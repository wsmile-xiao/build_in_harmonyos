#!/usr/bin/env sh
set -eu
if (set -o pipefail) 2>/dev/null; then
	set -o pipefail
fi

tool="$1"
tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/remrun-test.XXXXXX")"
trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM

check_success()
{
	name="$1"
	shift
	expected="$1"
	shift
	out="$tmpdir/$name.out"
	err="$tmpdir/$name.err"
	"$tool" "$@" >"$out" 2>"$err"
	grep -F -- "$expected" "$out" >/dev/null
}

check_failure()
{
	name="$1"
	shift
	expected="$1"
	shift
	out="$tmpdir/$name.out"
	err="$tmpdir/$name.err"
	if "$tool" "$@" >"$out" 2>"$err"; then
		echo "expected failure for $name" >&2
		return 1
	fi
	grep -F -- "$expected" "$err" >/dev/null
}

check_success version "remrun 0.2.5" --version
check_success features "Features: remrun=0.2.5 hostspec=1.0" --features
check_success help "Usage:" --help
check_failure bad-option "Invalid long option" --bad-option
check_failure missing-file "Not a readable regular file: /nonexistent" host /nonexistent
check_failure stdin-conflict 'The -s option may not be used with "-" as a filename' -s host -

echo "remrun test: OK"
