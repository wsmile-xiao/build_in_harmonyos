#!/bin/sh
# test_package/test_tmatrix.sh - real functional tests for tmatrix 1.4.
#
# tmatrix is a CLI application, so these tests drive the packaged executable and
# assert on its observable behaviour. The binary is an OHOS aarch64 ELF; the
# caller supplies a runner prefix when the build host cannot execute a foreign
# ABI directly (e.g. "qemu-aarch64 -L <sysroot>"). With no prefix the binary is
# executed as-is, which is what happens on a native OHOS worker.
#
# Why every invocation is time-bounded
# ------------------------------------
# A successful argument parse drops tmatrix into an endless render loop, so
# each run is wrapped in timeout(1). Note that a *rejected* command line is not
# distinguishable by exit status: upstream main() falls off the end of the if
# and returns 0 even after printing the diagnostic. The tests therefore key on
# the diagnostics, and treat "still running when the timer fired" as positive
# evidence that the render loop was reached.
#
# How the render path is observed
# -------------------------------
# Reaching the render loop means argument parsing accepted the options AND
# Terminal::Terminal() ran initscr(). What happens next depends on whether a
# terminfo database is reachable: with one, a frame is painted; without one,
# ncurses reports "cannot initialize terminal type" and exits. Both outcomes
# prove control got past the parser into the curses code, and both are absent
# when the parser rejects the options. render_entered() accepts either, plus
# the still-running case.
#
# Covered behaviour (each one reaches real tmatrix code):
#   T1  --version prints the compiled-in VERSION_NUMBER ("1.4", tmatrix.h).
#   T2  --help prints the full option table built from Parser's option array.
#   T3  An unknown option is rejected before the render path is entered.
#   T4  An out-of-range --steps-per-sec value is rejected the same way.
#   T5  A fractional --fall-speed range is accepted and the render path is
#       entered. Fractional speeds are the feature 1.4 added, and 0.4,1.7 is a
#       value the pre-1.4 integer-only parser could not take.
#   T6  Under a pseudo-terminal the render path either paints a frame or
#       reports the ncurses terminal-type error, while an out-of-range range
#       reaches neither.
#   T7  The artifact is a 64-bit AArch64 PIE ELF (HarmonyOS-specific artifact
#       assertion, read with the POSIX-required od(1) so no binutils are
#       needed).
#
# Usage: sh test_tmatrix.sh <tmatrix-binary> [runner args ...]
#
# Exit status: 0 = every assertion passed, 1 = at least one failed,
#              2 = harness/setup error.
set -u

BIN="${1:-}"
[ $# -gt 0 ] && shift
RUNNER_ARGS="$*"

[ -n "$BIN" ] || { echo "usage: $0 <tmatrix-binary> [runner args ...]" >&2; exit 2; }
[ -f "$BIN" ] || { echo "FAIL: tmatrix binary not found: $BIN" >&2; exit 2; }

if ! command -v timeout >/dev/null 2>&1; then
    echo "FAIL: timeout(1) is required to bound the tmatrix render loop" >&2
    exit 2
fi

# Seconds each invocation may run before it is considered to be in the render
# loop. Comfortably longer than argument parsing, short enough to keep the
# suite quick.
RUN_SECONDS=4

failures=0
checks=0
out=""
rc=0

# run <args...>: execute tmatrix with the given arguments, capture combined
# output into $out and the exit status into $rc. $RUNNER_ARGS is deliberately
# unquoted: it is a word list (runner plus its options), not a single path.
run() {
    out=$(timeout "$RUN_SECONDS" $RUNNER_ARGS "$BIN" "$@" 2>&1)
    rc=$?
}

# still_running <status>: timeout(1) reports 124 when it had to kill the
# process, 143 when the process died from the delivered SIGTERM.
still_running() {
    [ "$1" = "124" ] || [ "$1" = "143" ]
}

# render_entered <output> <status>: succeed when the run shows the process got
# past argument parsing into the curses code -- a painted escape sequence, the
# ncurses terminal-type diagnostic, or the loop still running at the timeout.
render_entered() {
    still_running "$2" && return 0
    printf '%s' "$1" | grep -qE "$(printf '\033')|cannot initialize terminal type"
}

check() {
    # check <description> <0 = pass>
    checks=$((checks + 1))
    if [ "$2" = "0" ]; then
        echo "PASS: $1"
    else
        echo "FAIL: $1"
        failures=$((failures + 1))
    fi
}

echo "--- tmatrix 1.4 test_package functional tests ---"
echo "binary: $BIN"
[ -n "$RUNNER_ARGS" ] && echo "runner: $RUNNER_ARGS"

# T1: --version reports the upstream version number.
run --version
printf '%s' "$out" | grep -q "tmatrix version 1\.4"
check "T1 --version prints 'tmatrix version 1.4' (rc=$rc)" $?

# T2: --help prints the full usage block built from the option table.
run --help
if printf '%s' "$out" | grep -q "Usage: tmatrix" &&
   printf '%s' "$out" | grep -q -- "--fall-speed" &&
   printf '%s' "$out" | grep -q -- "--steps-per-sec" &&
   printf '%s' "$out" | grep -q -- "--no-fade"; then
    r=0
else
    r=1
fi
check "T2 --help prints the option table (rc=$rc)" "$r"

# T3: an unknown option must be rejected before any terminal is set up.
run --definitely-not-an-option
if printf '%s' "$out" | grep -q "Unknown option" && ! render_entered "$out" "$rc"; then
    r=0
else
    r=1
fi
check "T3 unknown option is rejected before the render path (rc=$rc)" "$r"

# T4: a value outside the accepted range must be rejected the same way.
run --steps-per-sec=0
if printf '%s' "$out" | grep -qi "invalid value" && ! render_entered "$out" "$rc"; then
    r=0
else
    r=1
fi
check "T4 out-of-range --steps-per-sec is rejected (rc=$rc)" "$r"

# T5: a fractional fall-speed range -- the feature tmatrix 1.4 added -- must be
# accepted, so the process gets as far as the curses code.
run --no-fade --fall-speed=0.4,1.7
if printf '%s' "$out" | grep -qi "invalid value" || ! render_entered "$out" "$rc"; then
    r=1
else
    r=0
fi
check "T5 fractional --fall-speed=0.4,1.7 reaches the render path (rc=$rc)" "$r"

# T6: with a pty attached the render path paints a frame or reports the ncurses
# terminal-type error, while an out-of-range range reaches neither.
if command -v script >/dev/null 2>&1; then
    render_out=$(TERM=xterm timeout "$RUN_SECONDS" script -q -c \
        "$RUNNER_ARGS \"$BIN\" --no-fade --fall-speed=0.4,1.7" /dev/null 2>&1)
    render_rc=$?
    if render_entered "$render_out" "$render_rc"; then
        r=0
    else
        r=1
    fi
    check "T6 render path entered under a pty (rc=$render_rc)" "$r"

    # When a terminfo database is reachable the frame carries the bright
    # attribute the ColorTerminal constructor emits and the cursor-home
    # sequence Terminal::Flush() appends. Skipped, not failed, when the
    # database is unavailable in this environment.
    if printf '%s' "$render_out" | grep -q "$(printf '\033')\[0;0H"; then
        if printf '%s' "$render_out" | grep -q "$(printf '\033')\[1m"; then
            r=0
        else
            r=1
        fi
        check "T6b painted frame carries the bright-attribute sequence" "$r"
    else
        echo "SKIP: T6b no terminfo database reachable, frame not painted"
    fi

    # An out-of-range range must fail inside the parser, so no escape sequence
    # and no ncurses diagnostic may appear even with a pty attached.
    bad_out=$(TERM=xterm timeout "$RUN_SECONDS" script -q -c \
        "$RUNNER_ARGS \"$BIN\" --fall-speed=99,100" /dev/null 2>&1)
    bad_rc=$?
    if printf '%s' "$bad_out" | grep -qi "invalid value" &&
       ! render_entered "$bad_out" "$bad_rc"; then
        r=0
    else
        r=1
    fi
    check "T6c out-of-range --fall-speed=99,100 never reaches curses (rc=$bad_rc)" "$r"
else
    echo "SKIP: T6 needs the 'script' pty helper, absent here"
fi

# T7: the artifact really is a 64-bit AArch64 PIE ELF. Read straight from the
# ELF header with od(1): offset 0 magic, 4 EI_CLASS, 16 e_type, 18 e_machine.
hdr=$(od -An -tx1 -N20 "$BIN" | tr -d ' \n')
if [ "${hdr#7f454c46}" != "$hdr" ] &&
   [ "$(printf '%s' "$hdr" | cut -c9-10)" = "02" ] &&
   [ "$(printf '%s' "$hdr" | cut -c33-36)" = "0300" ] &&
   [ "$(printf '%s' "$hdr" | cut -c37-40)" = "b700" ]; then
    r=0
else
    r=1
    echo "  ELF header: $hdr"
fi
check "T7 artifact is a 64-bit AArch64 PIE ELF" "$r"

# Report the exact number of failed checks, not just a boolean, so a partial
# failure is never mistaken for a single-assertion failure.
echo "--- assertions: $checks, failures: $failures ---"
if [ "$failures" = "0" ]; then
    echo "--- tmatrix 1.4 test_package: ALL PASS ---"
else
    echo "--- tmatrix 1.4 test_package: FAILED ---"
fi
exit $failures
