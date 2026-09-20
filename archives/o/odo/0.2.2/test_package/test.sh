#!/bin/sh
# Consumer test for odo 0.2.2: exercises the packaged `odo` binary's real CLI.
# odo semantics (verified against upstream main.c):
#   default : atomic increment, no output
#   -c FILE : print current value without updating
#   -p FILE : increment AND print the new value
#   -s N FILE: set counter to N
#   -r FILE : reset counter to 0
# Output is unpadded decimal.
# Uses a temp dir under $TMPDIR (HMDFS /tmp is read-only on OHOS).

set -e

WORKDIR=$(mktemp -d ${TMPDIR:-/tmp}/odo-test.XXXXXX) || {
    echo "mktemp failed" >&2; exit 1
}
trap 'rm -rf "$WORKDIR"' EXIT
cd "$WORKDIR"

CFILE=count.odo

# 1. default increment creates the file with value 1; -c prints it unchanged
odo "$CFILE"
[ "$(odo -c "$CFILE")" = "1" ] || { echo "FAIL: initial increment" >&2; exit 1; }

# 2. increment again -> 2
odo "$CFILE"
[ "$(odo -c "$CFILE")" = "2" ] || { echo "FAIL: second increment" >&2; exit 1; }

# 3. -p increments and prints the new value
[ "$(odo -p "$CFILE")" = "3" ] || { echo "FAIL: increment+print" >&2; exit 1; }
[ "$(odo -c "$CFILE")" = "3" ] || { echo "FAIL: value after -p" >&2; exit 1; }

# 4. set a value -> 1234
odo -s 1234 "$CFILE"
[ "$(odo -c "$CFILE")" = "1234" ] || { echo "FAIL: set value" >&2; exit 1; }

# 5. -c never updates the value
odo -c "$CFILE" >/dev/null
[ "$(odo -c "$CFILE")" = "1234" ] || { echo "FAIL: cat must not update" >&2; exit 1; }

# 6. reset -> 0
odo -r "$CFILE"
[ "$(odo -c "$CFILE")" = "0" ] || { echo "FAIL: reset value" >&2; exit 1; }

echo "odo consumer test: all passed"
