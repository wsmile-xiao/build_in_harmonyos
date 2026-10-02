#!/usr/bin/env bash
# Verify that the packaged ParaFly runs commands and records their completion.
set -euo pipefail
umask 022

if [ -z "${PARAFLY_BIN:-}" ]; then
    echo "PARAFLY_BIN is not set" >&2
    exit 1
fi

work="$PWD/.parafly-test-$$"
mkdir "$work"
trap 'rm -rf "$work"' 0

printf 'printf alpha > %s/alpha\nprintf beta > %s/beta\nprintf gamma > %s/gamma\n' \
    "$work" "$work" "$work" > "$work/commands.txt"
(
    cd "$work"
    "$PARAFLY_BIN" -c commands.txt -CPU 2 -failed_cmds failed.txt
)

test "$(cat "$work/alpha")" = "alpha"
echo "        [ok] first command ran"
test "$(cat "$work/beta")" = "beta"
echo "        [ok] second command ran"
test "$(cat "$work/gamma")" = "gamma"
echo "        [ok] third command ran"
completed="$(wc -l < "$work/commands.txt.completed" | tr -d '[:space:]')"
test "$completed" = "3"
echo "        [ok] all commands recorded complete"
test ! -s "$work/failed.txt"
echo "        [ok] no failed commands"
echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test.sh","consumer_passed":5,"consumer_total":5}'
