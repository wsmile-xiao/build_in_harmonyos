#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for procenv 0.51 (installed bin/procenv).
#
# Really runs the installed binary and checks the output of sections that
# work on OHOS. Sections that busy-loop on OHOS (-b/--libs, -i/--misc and
# the no-argument full dump) are deliberately NOT invoked.
#
# Env: PROCENV_BIN = path to the installed procenv executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -euo pipefail

BIN="${PROCENV_BIN:-procenv}"
WORK="${TMPDIR:-.}/procenv-test.$$"
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
trap 'rm -rf "$WORK"' EXIT

checks=0
fails=0

check() { # check <name> <0|1>
	checks=$((checks + 1))
	if [ "$2" -eq 0 ]; then
		echo "PASS: $1"
	else
		echo "FAIL: $1"
		fails=$((fails + 1))
	fi
}

contains() { # contains <file> <pattern>
	if grep -q -- "$2" "$1"; then echo 0; else echo 1; fi
}

# 1. version
"$BIN" --version > "$WORK/version.out" 2>&1
check "procenv --version reports 0.51" "$(contains "$WORK/version.out" "0.51")"

# 2. JSON output (must look like JSON: start with '{' and contain a colon)
"$BIN" --format=json --uname > "$WORK/uname.json" 2>&1
if head -c 1 "$WORK/uname.json" | grep -q "{"; then r=0; else r=1; fi
if [ "$(contains "$WORK/uname.json" ":")" -ne 0 ]; then r=1; fi
check "procenv --format=json --uname emits JSON" "$r"

# 3. XML output
"$BIN" --format=xml --sysconf > "$WORK/sysconf.xml" 2>&1
check "procenv --format=xml --sysconf emits XML" "$(contains "$WORK/sysconf.xml" "<procenv")"

# 4. limits section
"$BIN" --limits > "$WORK/limits.out" 2>&1
check "procenv --limits prints the limits section" "$(contains "$WORK/limits.out" "limits:")"

# 5. environment section
"$BIN" --environment > "$WORK/environment.out" 2>&1
check "procenv --environment prints PATH" "$(contains "$WORK/environment.out" "PATH")"

echo "PROCENV_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
