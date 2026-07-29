#!/bin/bash
# Verify the packaged binary, command execution, and exclusive lock behavior.

set -euo pipefail

LOCKRUN_BIN="${1:-}"
holder_pid=""
tmpdir=""

cleanup() {
    if [ -n "$holder_pid" ]; then
        kill "$holder_pid" 2>/dev/null || true
        wait "$holder_pid" 2>/dev/null || true
    fi
    if [ -n "$tmpdir" ]; then
        rm -rf "$tmpdir"
    fi
}
trap cleanup EXIT

if [ -z "$LOCKRUN_BIN" ]; then
    echo "ERROR: lockrun binary path is required"
    exit 1
fi

if [ ! -x "$LOCKRUN_BIN" ]; then
    echo "ERROR: $LOCKRUN_BIN not found or not executable"
    exit 1
fi

version_output="$("$LOCKRUN_BIN" --version)"
if ! printf "%s\n" "$version_output" | grep -Fq "lockrun 1.1.3"; then
    echo "ERROR: unexpected lockrun version output"
    printf "%s\n" "$version_output"
    exit 1
fi

tmpdir="$(mktemp -d)"
lockfile="$tmpdir/lockrun-test.lock"
single_marker="$tmpdir/single-command-ran"
holder_started="$tmpdir/holder-started"
holder_finished="$tmpdir/holder-finished"
overlap_marker="$tmpdir/overlap-command-ran"

"$LOCKRUN_BIN" --lockfile="$lockfile" -- "$BASH" -c 'touch "$1"' lockrun "$single_marker"
if [ ! -f "$single_marker" ]; then
    echo "ERROR: command wrapped by lockrun did not execute"
    exit 1
fi
if [ ! -f "$lockfile" ]; then
    echo "ERROR: lock file was not created"
    exit 1
fi

set +e
"$LOCKRUN_BIN" --lockfile="$tmpdir/exec-failure.lock" -- \
    "$tmpdir/command-does-not-exist" >"$tmpdir/exec-failure.out" 2>&1
exec_failure_status=$?
set -e
if [ "$exec_failure_status" -eq 0 ]; then
    echo "ERROR: missing child command unexpectedly returned success"
    cat "$tmpdir/exec-failure.out"
    exit 1
fi
if ! grep -Fq "ERROR: cannot execute" "$tmpdir/exec-failure.out"; then
    echo "ERROR: missing child command did not report the exec failure"
    cat "$tmpdir/exec-failure.out"
    exit 1
fi

"$LOCKRUN_BIN" --lockfile="$lockfile" -- "$BASH" -c \
    'touch "$1"; sleep 6; touch "$2"' lockrun "$holder_started" "$holder_finished" &
holder_pid=$!

for _ in 1 2 3 4 5; do
    if [ -f "$holder_started" ]; then
        break
    fi
    sleep 1
done
if [ ! -f "$holder_started" ]; then
    echo "ERROR: lock holder did not start"
    exit 1
fi

set +e
"$LOCKRUN_BIN" --lockfile="$lockfile" -- "$BASH" -c \
    'touch "$1"' lockrun "$overlap_marker" >"$tmpdir/overlap.out" 2>&1
overlap_status=$?
set -e

if [ "$overlap_status" -eq 0 ]; then
    echo "ERROR: overlapping invocation unexpectedly acquired the lock"
    cat "$tmpdir/overlap.out"
    exit 1
fi
if [ -f "$overlap_marker" ]; then
    echo "ERROR: command from rejected overlapping invocation was executed"
    exit 1
fi

if ! wait "$holder_pid"; then
    echo "ERROR: lock holder command failed"
    holder_pid=""
    exit 1
fi
holder_pid=""
if [ ! -f "$holder_finished" ]; then
    echo "ERROR: lock holder command did not finish"
    exit 1
fi

echo "PASS: lockrun completed 10/10 checks, including exec and lock rejection"
