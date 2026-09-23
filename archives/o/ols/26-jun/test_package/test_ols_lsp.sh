#!/usr/bin/env sh
# ols LSP initialize handshake test (POSIX sh, busybox compatible).
#
# Real functional test of the ols binary (R34): pipes a JSON-RPC 2.0
# initialize/shutdown/exit sequence over stdin and asserts ols responds
# with a Content-Length framed message containing a "result" object.
#
# Usage: test_ols_lsp.sh <stdin.jsonrpc> <builtin_dir> <ols_bin>
#
# Note: OHOS busybox sh has no PIPESTATUS and no `local`; exit code of the
# ols process is captured to a temp file after it finishes (no `set -e`
# around the invocation so a non-zero ols exit is not masked).

# Temp files; clean up ALL of them on exit.
RCFILE=$(mktemp)
trap 'rm -f "$RCFILE" "$RCFILE.out" "$RCFILE.err"' EXIT

# Run ols with stdin piped; capture stdout/stderr separately and RC.
OLS_BUILTIN_FOLDER="$2" "$3" < "$1" >"$RCFILE.out" 2>"$RCFILE.err"
RC=$?

# Surface stderr regardless of pass/fail so CI can diagnose.
if [ -s "$RCFILE.err" ]; then
    cat "$RCFILE.err" >&2
fi

if [ "$RC" -ne 0 ]; then
    echo "FAIL: ols exited rc=$RC" >&2
    exit 1
fi

OUT=$(cat "$RCFILE.out")
if [ -z "$OUT" ]; then
    echo "FAIL: ols produced no output" >&2
    exit 1
fi

echo "$OUT"

# Assert LSP handshake: a Content-Length frame and a JSON-RPC result.
if echo "$OUT" | grep -q "Content-Length:"; then
    if echo "$OUT" | grep -q '"result"'; then
        echo "PASS: ols LSP initialize handshake succeeded"
        exit 0
    fi
    echo "FAIL: no JSON-RPC result in output" >&2
    exit 1
fi
echo "FAIL: no Content-Length in output" >&2
exit 1