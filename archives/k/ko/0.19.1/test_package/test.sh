#!/data/service/hnp/bin/bash
# test_package/test.sh — HarmonyOS consumer smoke tests for the packaged ko binary.
# Runs in conanrun env (PATH includes the installed bin/).
# Three consumer test cases, each prints "[ok] ..." on success / "[fail] ..." on failure.
set -uo pipefail

if [ "$#" -ne 1 ]; then
    echo "[fail] usage: $0 <path-to-ko>" >&2
    exit 2
fi

ko_bin="$1"
fails=0

# ── Case 1: `ko version` reports the packaged version ──────────────────────
version_output="$("$ko_bin" version 2>&1)"
rc=$?
if [ $rc -eq 0 ] && printf '%s\n' "$version_output" | grep -F "v0.19.1" >/dev/null; then
    echo "[ok] ko version reports v0.19.1 (output: $version_output)"
else
    echo "[fail] ko version rc=$rc output: $version_output"
    fails=$((fails+1))
fi

# ── Case 2: `ko help` lists the real subcommand surface (cobra root) ────────
# Actual subcommand set of ko 0.19.1 (from `ko help`): apply build completion
# create delete help login resolve run version.
help_output="$("$ko_bin" help 2>&1)"
rc=$?
missing=""
for sub in build apply create resolve run delete login version; do
    printf '%s\n' "$help_output" | grep -E "(^| )$sub( |$)" >/dev/null || missing="$missing $sub"
done
if [ $rc -eq 0 ] && [ -z "$missing" ]; then
    echo "[ok] ko help lists all core subcommands (build/apply/create/resolve/run/delete/login/version)"
else
    echo "[fail] ko help rc=$rc missing subcommands:$missing"
    fails=$((fails+1))
fi

# ── Case 3: `ko completion bash` exercises the real cobra completion path ───
# bash completion V2 for ko defines __ko_* helpers (e.g. __ko_get_completion_results).
completion_output="$("$ko_bin" completion bash 2>&1)"
rc=$?
if [ $rc -eq 0 ] && printf '%s\n' "$completion_output" | grep -F "__ko_get_completion_results" >/dev/null; then
    echo "[ok] ko completion bash generated a valid bash completion script"
else
    echo "[fail] ko completion bash rc=$rc (no __ko_get_completion_results marker in output)"
    fails=$((fails+1))
fi

if [ "$fails" -eq 0 ]; then
    echo "[ok] all 3 HarmonyOS consumer test cases passed"
    exit 0
fi
echo "[fail] $fails of 3 HarmonyOS consumer test cases failed"
exit 1
