#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for xe 1.0 (installed bin/xe).
#
# Really runs the installed binary and checks its output for the input modes
# that do not depend on the environment.
#
# Env: XE_BIN = path to the installed xe executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

BIN="${XE_BIN:-xe}"
WORK="${TMPDIR:-.}/xe-test.$$"
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
trap 'rm -rf "$WORK"' EXIT

checks=0
fails=0

check() { # check <name> <actual> <expected>
	checks=$((checks + 1))
	if [ "$2" = "$3" ]; then
		echo "PASS: $1"
	else
		echo "FAIL: $1 (got '$2', want '$3')"
		fails=$((fails + 1))
	fi
}

# 1. default: one argument per command invocation
got=$(printf 'a\nb\nc\n' | "$BIN" echo | tr '\n' ',')
check "xe echo runs once per line" "$got" "a,b,c,"

# 2. -N2 batching
got=$(printf '1\n2\n3\n4\n5\n' | "$BIN" -N2 echo | tr '\n' ',')
check "xe -N2 batches two per run" "$got" "1 2,3 4,5,"

# 3. -N0 single run with all arguments
got=$(printf '1\n2\n3\n' | "$BIN" -N0 echo | tr '\n' ',')
check "xe -N0 passes all arguments at once" "$got" "1 2 3,"

# 4. {} replacement
got=$(printf '1\n2\n3\n' | "$BIN" echo a {} x | tr '\n' ',')
check "xe replaces {} in place" "$got" "a 1 x,a 2 x,a 3 x,"

# 5. -0 NUL-separated input
got=$(printf 'foo\0bar\0quux' | "$BIN" -0 echo | tr '\n' ',')
check "xe -0 reads NUL-separated input" "$got" "foo,bar,quux,"

# 6. -n dry run prints the commands (to stderr) instead of executing
got=$(printf 'a\nb\nc\n' | "$BIN" -n echo x 2>&1 | tr '\n' ',')
check "xe -n dry run prints commands" "$got" "echo x a,echo x b,echo x c,"

echo "XE_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
