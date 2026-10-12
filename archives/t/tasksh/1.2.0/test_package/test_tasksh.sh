#!/usr/bin/env bash
# test_package/test_tasksh.sh — real functional tests for the tasksh binary.
#
# tasksh is an interactive REPL around Taskwarrior: it reads a prompt, reads one
# command from stdin, dispatches it, and loops until EOF / exit / quit. Driving
# it over a pipe (stdin is not a tty) exercises the real command loop including
# readline() line reading, so every assertion below runs the packaged ELF.
#
# usage: test_tasksh.sh <tasksh_bin> [<task_bin>]
set -u

TSH="${1:-}"
TASK="${2:-}"

fail() { echo "FAIL: $*" >&2; exit 1; }
ok()   { echo "  [ok] $*"; }

[ -n "$TSH" ] || fail "usage: test_tasksh.sh <tasksh_bin> [<task_bin>]"
[ -x "$TSH" ] || fail "tasksh not found or not executable: $TSH"

# shellcheck source=runner.sh
. "$(dirname "$0")/runner.sh"

# tasksh never aborts on a bare command: the REPL returns 0 for exit/quit/EOF.
tsh() {
    # stdin: commands, one per line.
    printf '%s\n' "$@" | tsh_run
}

# ─── T1: --version prints the bare version, no Taskwarrior needed ───────────
OUT=$(tsh_run --version) || fail "--version exited non-zero"
[ "$OUT" = "1.2.0" ] || fail "--version printed '$OUT', expected exactly '1.2.0'"
ok "T1 --version == 1.2.0 (exact match, no task binary invoked)"

# ─── T2: --version with extra args must NOT short-circuit into the REPL ──────
# argc == 2 is the only short-circuit; anything else falls into the REPL, which
# reads stdin. Feeds "exit" so the REPL terminates cleanly.
OUT=$(tsh_run --version extra </dev/null) || fail "REPL path exited non-zero"
case "$OUT" in
    *"1.2.0"*) fail "--version extra short-circuited and printed the version" ;;
    *) ok "T2 argc!=2 falls through to the command loop (no version short-circuit)" ;;
esac

# ─── T3: `help` renders the built-in command table ──────────────────────────
OUT=$(tsh "help" "exit")
echo "$OUT" | grep -q "Commands:" || fail "help did not print the command table"
echo "$OUT" | grep -q "tasksh> review" || fail "help missing 'review' entry"
echo "$OUT" | grep -q "tasksh> diagnostics" || fail "help missing 'diagnostics' entry"
echo "$OUT" | grep -q "tasksh> exec" || fail "help missing 'exec' entry"
ok "T3 help renders command table (review / diagnostics / exec)"

# ─── T4: `exec <cmd>` escapes to the shell ───────────────────────────────────
OUT=$(tsh "exec echo TASKSH_EXEC_MARKER" "exit")
echo "$OUT" | grep -q "TASKSH_EXEC_MARKER" \
    || fail "exec escape did not run the shell command; got: $OUT"
ok "T4 'exec echo' runs the shell command and returns its output"

# ─── T5: `!<cmd>` is the short form of exec ─────────────────────────────────
OUT=$(tsh "!echo TASKSH_BANG_MARKER" "exit")
echo "$OUT" | grep -q "TASKSH_BANG_MARKER" \
    || fail "'!' escape did not run the shell command; got: $OUT"
ok "T5 '!echo' short-form escape runs the shell command"

# ─── T6: `diagnostics` reports the linked Readline version ───────────────────
# This is the assertion that proves the static libreadline.a actually linked and
# that HAVE_READLINE was defined: the field prints the RL_VERSION_* macros read
# out of <readline/readline.h>. It would read "n/a" without Readline.
OUT=$(tsh "diagnostics" "exit")
echo "$OUT" | grep -q "libreadline: 8.3" \
    || fail "diagnostics did not report 'libreadline: 8.3'; got: $OUT"
echo "$OUT" | grep -q "tasksh 1.2.0" || fail "diagnostics missing product banner"
echo "$OUT" | grep -q "Compliance: C++" || fail "diagnostics missing compiler compliance"
ok "T6 diagnostics reports tasksh 1.2.0 + libreadline 8.3 (static readline linked)"

# ─── T7: non-builtin commands are delegated to Taskwarrior ─────────────────
# Unknown verbs are rewritten to "task <verb>" and handed to the shell; tasksh
# echoes the rewritten command line before invoking it, which is observable
# whether or not `task` is installed.
OUT=$(tsh "add conan tasksh roundtrip" "exit")
echo "$OUT" | grep -q "\[task add conan tasksh roundtrip\]" \
    || fail "arbitrary command was not delegated as 'task ...'; got: $OUT"
ok "T7 arbitrary command delegated to Taskwarrior as 'task <cmd>'"

# ─── T8: round-trip against the real Taskwarrior when it is available ───────
# Strongest assertion: with task/2.6.2 on PATH, add a task through tasksh and
# read it back with task. Skipped (not failed) when task is absent — tasksh
# itself is still fully exercised by T1-T7.
if [ -n "$TASK" ] && [ -x "$TASK" ]; then
    TD=$(mktemp -d)
    export TASKDATA="$TD/data"
    export TASKRC="$TD/taskrc"
    mkdir -p "$TASKDATA"
    printf 'data.location=%s\n' "$TASKDATA" > "$TASKRC"

    OUT=$(tsh "add tasksh roundtrip task" "exit")
    echo "$OUT" | grep -q "\[task add tasksh roundtrip task\]" \
        || fail "tasksh did not delegate the add; got: $OUT"

    LIST=$("$TASK" rc.verbose:nothing list 2>&1 || true)
    echo "$LIST" | grep -q "tasksh roundtrip task" \
        || fail "task created through tasksh is not visible to 'task list'; got: $LIST"
    ok "T8 round-trip: task added via tasksh is listed by taskwarrior"

    rm -rf "$TD"
    unset TASKDATA TASKRC
else
    echo "  [skip] T8 round-trip: taskwarrior binary not provided to this test"
fi

# ─── T9: EOF on stdin terminates the REPL with status 0 ─────────────────────
printf '' | tsh_run >/dev/null 2>&1
RC=$?
[ "$RC" -eq 0 ] || fail "immediate EOF exited $RC, expected 0"
ok "T9 EOF on stdin exits 0"

# ─── T10: `quit` terminates the REPL with status 0 ─────────────────────────
printf 'quit\n' | tsh_run >/dev/null 2>&1
RC=$?
[ "$RC" -eq 0 ] || fail "'quit' exited $RC, expected 0"
ok "T10 'quit' exits 0"

# ─── T11: `exit` terminates the REPL with status 0 ─────────────────────────
printf 'exit\n' | tsh_run >/dev/null 2>&1
RC=$?
[ "$RC" -eq 0 ] || fail "'exit' exited $RC, expected 0"
ok "T11 'exit' exits 0"

# ─── T12: `review` subcommand is reachable (dispatch, not a crash) ───────────
# review drives the interactive task-review session. Without a terminal it
# still must be dispatched and return to the prompt rather than abort.
OUT=$(tsh "review" "exit")
case "$OUT" in
    *"Unknown error."*) fail "'review' hit the catch-all handler; got: $OUT" ;;
esac
ok "T12 'review' dispatches without hitting the catch-all error handler"

echo "=== tasksh: all assertions passed ==="