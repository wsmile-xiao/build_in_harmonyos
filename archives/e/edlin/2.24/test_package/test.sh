#!/bin/sh
# test_package/test.sh — smoke tests for the installed edlin binary.
# edlin is an interactive line editor driven entirely by stdin commands:
#   I        enter insert mode (lines until a single '.')
#   E        write buffer to file and exit
#   L        list buffer
# Upstream ships no test suite, so these assertions exercise the installed
# package end-to-end: open a file, insert text, save, re-open, list.

set -u

fails=0
check() {
    # check <label> <condition-result>
    if [ "$2" = "0" ]; then
        echo "PASS: $1"
    else
        echo "FAIL: $1"
        fails=$((fails + 1))
    fi
}

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# --- Test 1: insert lines into a new file and save with e (4 assertions) ---
# NOTE: quit commands prompt "Really quit (Y/n)?" — answer Y so the editor
# exits cleanly; with plain EOF it abort()s (upstream interactive semantic).
# NOTE: the save-and-exit command must be lowercase 'e': upstream matches
# case-insensitively in the command switch but re-checks the raw char
# (`*ip == 'e'`) when deciding whether to exit, so uppercase 'E' saves the
# file but never exits (documented upstream quirk, not patched here).
f="$tmp/new.txt"
printf '1I\nhello from edlin\nsecond line\n.\ne\nY\n' | edlin "$f" >/dev/null 2>&1
check "T1 exit code is 0 after e" "$?"
[ -f "$f" ]; check "T1 output file created" "$?"
grep -q "hello from edlin" "$f"; check "T1 line 1 content saved" "$?"
grep -q "second line" "$f"; check "T1 line 2 content saved" "$?"

# --- Test 2: open existing file, no-op quit with e (2 assertions) ---
printf 'e\nY\n' | edlin "$f" >/dev/null 2>&1
check "T2 exit code is 0 on no-op edit" "$?"
grep -q "second line" "$f"; check "T2 existing content preserved" "$?"

# --- Test 3: list command echoes buffer on stdout (2 assertions) ---
out="$(printf 'L\nQ\nY\n' | edlin "$f" 2>/dev/null)"
[ "$?" = "0" ]; check "T3 exit code is 0 on L+Q" "$?"
echo "$out" | grep -q "hello from edlin"; check "T3 list prints buffer line" "$?"

echo "test.sh: $fails failing assertion(s)"
[ "$fails" = "0" ]
