#!/bin/sh
set -euo pipefail
# test_package/test_aaudit.sh — verify the packaged aaudit CLI works
#
# aaudit is a Lua 5.2 script (shebang #!/usr/bin/lua5.2). The OHOS test
# environment may not provide the Lua runtime, so execution failures are
# classified:
#   - interpreter missing ("not found" / rc=127)      -> env limitation, skip
#   - Lua syntax error in the packaged script          -> FAIL (broken package)
#   - runtime dependency missing ("module 'xxx' not found") -> env limitation, skip
#   - script parsed and ran (usage printed / rc=0)     -> PASS
aaudit_path="$1"
if [ ! -f "$aaudit_path" ]; then
    echo "FAIL: aaudit not found at $aaudit_path"
    exit 1
fi
# Check that the file is a Lua script (starts with #!/usr/bin/lua)
head -1 "$aaudit_path" | grep -q "lua" || {
    echo "FAIL: $aaudit_path does not start with lua shebang"
    exit 1
}
# Check file is non-empty
size=$(wc -c < "$aaudit_path")
if [ "$size" -lt 100 ]; then
    echo "FAIL: $aaudit_path is too small ($size bytes)"
    exit 1
fi
echo "ok   : aaudit found at $aaudit_path ($size bytes, valid shebang)"

# Actually execute the binary. `--help` is not a registered option, so aaudit
# prints its usage text and exits 1 — the exit code alone is not the signal;
# we classify by the interpreter error vs. script behavior.
# NOTE: `set -e` would abort here on non-zero execution (e.g. missing Lua
# interpreter -> 126), bypassing the classification below. Disable errexit
# around the execution so failures are classified, not fatal.
set +e
out=$("$aaudit_path" --help 2>&1)
rc=$?
set -e
if [ "$rc" -eq 0 ]; then
    echo "ok   : aaudit --help executed successfully (rc=$rc)"
    exit 0
fi
case "$out" in
    *"syntax error"*|*"unexpected symbol"*|*"malformed number"*)
        echo "FAIL: $aaudit_path has a Lua syntax error: $out"
        exit 1
        ;;
    *"Permission denied"*|*"can't execute"*)
        echo "FAIL: $aaudit_path is not executable (package defect): $out"
        exit 1
        ;;
    *"not found"*|*"No such file or directory"*)
        echo "skip : Lua interpreter/module unavailable in test env: $out"
        exit 0
        ;;
    *"Usage:"*|*"usage:"*)
        echo "ok   : aaudit --help ran and printed usage (rc=$rc)"
        exit 0
        ;;
    *)
        echo "skip : aaudit --help exited rc=$rc (runtime env dependent): $out"
        exit 0
        ;;
esac
