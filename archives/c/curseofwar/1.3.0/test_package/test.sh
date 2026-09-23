#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for the curseofwar executable.
# Runs inside the conanrun env (PATH includes the installed bin/ and
# TERMINFO points at the packaged ncurses terminfo database).
#
# Test 1: `curseofwar -v` prints exactly "1.3.0" (exits before ncurses UI).
# Test 2: `curseofwar -h` prints the help screen mentioning the game name.
# Test 3: game initialization + main game loop smoke — run the real game
#         headless for a few seconds; assert the map was generated, the
#         in-game Date advanced past its start (proving the simulate()
#         game loop ticks), and the terminal was restored with a full
#         endwin escape sequence on termination.
set -euo pipefail

GAME="${1:?usage: test.sh /path/to/curseofwar}"
GAME="$(readlink -f "${GAME}")"
OUT="$(mktemp "${TMPDIR:-/tmp}/cow-smoke.XXXXXX")"
trap 'rm -f "${OUT}"' EXIT

# Headless terminal setup for the ncurses UI: TERM is mandatory for
# initscr(). Force xterm — the CI/conan environment may carry an
# unsuitable TERM (e.g. ansi renders the date line differently and the
# escape-sequence assertions below expect xterm-style output), and the
# test must be deterministic regardless of the ambient environment.
# TERMINFO: normally exported by the conanrun env (ncurses runenv_info).
# Fallback: probe both conan cache roots (local ~/.conan2 and the CI
# worker ~/.cache/conan2) for the packaged ncurses terminfo database —
# the p/ folder name is a hash but always starts with "ncurs".
export TERM="xterm"
if [ -z "${TERMINFO:-}" ] && [ -z "${TERMINFO_DIRS:-}" ]; then
    # A cached ncurses package only qualifies when it actually ships the
    # xterm entry we force below (some cached builds strip the database).
    for base in "$HOME/.conan2/p" "$HOME/.cache/conan2/p"; do
        for TI in "$base"/ncurs*/p/share/terminfo; do
            if [ -f "${TI}/x/xterm" ]; then
                export TERMINFO="${TI}"
                break 2
            fi
        done
    done
fi
echo "TERM=${TERM} TERMINFO=${TERMINFO:-<unset>} TERMINFO_DIRS=${TERMINFO_DIRS:-<unset>}"

# ---------------------------------------------------------------- Test 1/3
echo "[test 1/3] curseofwar -v"
# Upstream main-common.c prints the version and then returns 1 from
# get_options() — a non-zero exit code is the *expected* behaviour here,
# so it must be captured without tripping errexit.
set +e
VER="$("${GAME}" -v 2>&1)"
RC=$?
set -e
[ "${RC}" = "1" ] || {
    echo "FAIL: curseofwar -v exited with rc=${RC}, expected 1 (version + exit)"
    exit 1
}
echo "curseofwar -v output: ${VER}"
[ "${VER}" = "1.3.0" ] || {
    echo "FAIL: curseofwar -v printed [${VER}], expected [1.3.0]"
    exit 1
}
echo "PASS: version is exactly 1.3.0"

# ---------------------------------------------------------------- Test 2/3
echo "[test 2/3] curseofwar -h"
HELP="$("${GAME}" -h 2>&1)" || true
[ -n "${HELP}" ] || {
    echo "FAIL: curseofwar -h produced empty output"
    exit 1
}
echo "${HELP}" | grep -qi "Command line arguments" || {
    echo "FAIL: curseofwar -h output does not contain the arguments section"
    exit 1
}
echo "${HELP}" | grep -qi "Written by Alexey Nikolaev" || {
    echo "FAIL: curseofwar -h output does not contain the author banner"
    exit 1
}
echo "PASS: help screen is non-empty with arguments section and author banner"

# ---------------------------------------------------------------- Test 3/3
echo "[test 3/3] game loop smoke (headless, fixed seed 42)"
# Fixed seed -R 42 makes the run reproducible. stdin closed: the game
# runs its real-time loop until SIGTERM. 6 seconds gives the loop plenty
# of ticks (10ms timer -> hundreds of simulate() rounds).
set +e
timeout 6 "${GAME}" -W 20 -H 15 -R 42 < /dev/null > "${OUT}" 2>&1
RC=$?
set -e
# timeout(1) reports 124 when it had to send SIGTERM — the expected path
# for a game that runs until stopped.
[ "${RC}" = "124" ] || {
    echo "FAIL: game exited with rc=${RC}, expected 124 (SIGTERM via timeout)"
    tail -c 300 "${OUT}" | tr -d '\033'
    exit 1
}
grep -aq "Map is generated" "${OUT}" || {
    echo "FAIL: game did not render the initial map generation screen"
    tail -c 300 "${OUT}" | tr -d '\033'
    exit 1
}
# The in-game date starts at 1878-05-12; after several seconds of
# real-time simulation the Date field must have advanced past the start.
grep -aq "Date:" "${OUT}" || {
    echo "FAIL: game did not render the status bar (Date field missing)"
    tail -c 300 "${OUT}" | tr -d '\033'
    exit 1
}
# The in-game calendar starts at (1850 + rand()%100) years and the
# real-time loop advances it every game tick. ncurses only redraws the
# day-of-month digits when they change, emitting "ESC[19d<DD>" updates
# on the date line. A growing sequence of such day updates proves that
# state_init() completed and the kings_move()/simulate() game loop is
# really ticking (not a frozen first frame).
DAY_UPDATES="$(grep -ao $'\033\[19d[0-9][0-9]' "${OUT}" | wc -l | tr -d ' ')"
if [ "${DAY_UPDATES}" -lt 2 ]; then
    echo "FAIL: in-game date did not advance (only ${DAY_UPDATES} day updates) — game loop not running"
    tail -c 300 "${OUT}" | tr -d '\033'
    exit 1
fi
echo "game loop is running: ${DAY_UPDATES} in-game day updates observed"
# Full terminal restoration (endwin) — ncurses cleanup ran on SIGTERM.
# The [?1049l (leave alternate screen) sequence appears exactly once,
# at the very end of the stream.
grep -aq $'\033\[?1049l' "${OUT}" || {
    echo "FAIL: terminal was not restored (endwin sequence missing)"
    tail -c 200 "${OUT}" | tr -d '\033'
    exit 1
}
echo "PASS: map generated, game loop advanced the clock, terminal restored"
