#!/bin/sh
# test_pioneers.sh — exercise every packaged pioneers executable (R34).
#
# Usage: test_pioneers.sh <bin_dir> <result_file> [fixture_dir]
#
# Assertions:
#   Contract smoke (6): headless trio answers --version with "15.6" banner;
#   GTK3 trio parses --help through GOption before gtk_init (display-less).
#   Integration (2):  pioneers-server-console loads an upstream .game file and
#   enters the "Preparing game" state; pioneers-metaserver starts and stays
#   alive (game directory service).  Both prove real code paths beyond the
#   version banner.
#
# Writes into <result_file>:
#   discovered <N>   number of assertions attempted
#   passed     <M>   number of assertions that succeeded
set -u

BIN_DIR="$1"
RESULT_FILE="$2"
FIXTURE_DIR="${3:-}"

discovered=0
passed=0

record() {  # record <0|1>  — 1 = assertion passed
    if [ "$1" -eq 1 ]; then
        passed=$((passed + 1))
    fi
}

# ── 1. Contract smoke ───────────────────────────────────────────
run_and_count() {
    prog="$1"
    mode="$2"
    discovered=$((discovered + 1))
    case "$mode" in
        version)
            out=$("$BIN_DIR/$prog" --version 2>/dev/null) || true
            case "$out" in
                *"15.6"*) record 1 ;;
                *) record 0 ;;
            esac
            ;;
        help)
            if "$BIN_DIR/$prog" --help >/dev/null 2>&1; then
                record 1
            else
                record 0
            fi
            ;;
    esac
}

# Headless programs: functional --version banner check.
run_and_count pioneers-server-console version
run_and_count pioneers-metaserver version
run_and_count pioneersai version

# GTK3 programs: GOption --help exits 0 before gtk_init (no display needed).
run_and_count pioneers help
run_and_count pioneers-editor help
run_and_count pioneers-server-gtk help

# ── 2. Integration: real game session ───────────────────────────
if [ -n "$FIXTURE_DIR" ] && [ -f "$FIXTURE_DIR/small.game" ]; then
    game_file="$FIXTURE_DIR/small.game"

    # IT-1: server loads an upstream game definition and prepares a session.
    discovered=$((discovered + 1))
    logf="${RESULT_FILE}.srv.$$"
    "$BIN_DIR/pioneers-server-console" --file "$game_file" -P 2 \
        -p 25560 >"$logf" 2>&1 &
    srv_pid=$!
    sleep 4
    if kill -0 "$srv_pid" 2>/dev/null \
            && grep -q "Preparing game" "$logf" 2>/dev/null; then
        record 1
    else
        record 0
    fi
    kill "$srv_pid" 2>/dev/null
    wait "$srv_pid" 2>/dev/null
    rm -f "$logf"

    # IT-2: metaserver (game directory service) starts and stays alive.
    discovered=$((discovered + 1))
    logm="${RESULT_FILE}.meta.$$"
    "$BIN_DIR/pioneers-metaserver" -p 25557-25560 >"$logm" 2>&1 &
    meta_pid=$!
    sleep 3
    if kill -0 "$meta_pid" 2>/dev/null; then
        record 1
    else
        record 0
    fi
    kill "$meta_pid" 2>/dev/null
    wait "$meta_pid" 2>/dev/null
    rm -f "$logm"
else
    # No fixture available: keep the run honest by declaring 2 skips.
    discovered=$((discovered + 2))
fi

echo "discovered $discovered" > "$RESULT_FILE"
echo "passed $passed" >> "$RESULT_FILE"
