#!/data/service/hnp/bin/bash
# test_package/test.sh — qodem 1.0.1 consumer checks
# Usage: test.sh <writable-output-dir> <terminfo-dir>
# Runs under the conanrun environment (PATH has the installed bin/).  Every
# input is fed from /dev/null so a keep-open CI stdin can never make the
# program wait for EOF.
set -u

OUT="${1:?usage: test.sh <output-dir> <terminfo-dir>}"
TERM_DIR="${2:-}"
mkdir -p "$OUT"

# conan's VirtualRunEnv pins TERM=dumb (it strips escapes from build logs).
# A curses program needs a real terminal type.
if [ -z "${TERM:-}" ] || [ "$TERM" = "dumb" ]; then
    export TERM=xterm
fi

# terminfo lives inside the ncurses dependency package.
if [ -n "$TERM_DIR" ] && [ -d "$TERM_DIR" ]; then
    export TERMINFO="$TERM_DIR"
    export TERMINFO_DIRS="$TERM_DIR"
fi

echo "[env] TERM=$TERM TERMINFO=${TERMINFO:-<unset>}"

CHECKS=0
FAILURES=0

ok() {
    CHECKS=$((CHECKS + 1))
    if [ "$2" -eq 0 ]; then
        echo "[ok]   $1"
    else
        FAILURES=$((FAILURES + 1))
        echo "[FAIL] $1"
    fi
}

echo "== 1. qodem --version (banner, no curses) =="
# 0002 makes the informational options exit with success (POSIX/GNU coding
# standards); stock upstream returned EXIT_VERSION(2) / EXIT_HELP(1) here.
qodem --version < /dev/null > "$OUT/version.txt" 2>&1
ok "qodem --version exits 0" $?
grep -q "qodem version 1.0.1" "$OUT/version.txt"
ok "--version reports qodem version 1.0.1" $?

echo "== 2. qodem --help (usage text, no curses) =="
qodem --help < /dev/null > "$OUT/help.txt" 2>&1
ok "qodem --help exits 0" $?
grep -q "terminal emulator" "$OUT/help.txt"
ok "--help describes a terminal emulator" $?

echo "== 3. qodem --create-config (option table + filesystem) =="
rm -f "$OUT/qodem.conf"
qodem --create-config "$OUT/qodem.conf" < /dev/null > "$OUT/create-config.txt" 2>&1
ok "qodem --create-config exits 0" $?
[ -s "$OUT/qodem.conf" ]
ok "options file is non-empty" $?
grep -q "emulation" "$OUT/qodem.conf"
ok "options file contains emulation defaults" $?

echo "== 4. terminal session through forkpty + ncurses (capture file) =="
rm -f "$OUT/cap.txt"
qodem --exit-on-completion --capfile "$OUT/cap.txt" uname < /dev/null \
    > "$OUT/session.txt" 2>&1
ok "qodem session exits 0" $?
[ -s "$OUT/cap.txt" ]
ok "capture file is non-empty" $?
grep -q "BEGIN" "$OUT/cap.txt"
ok "capture file has the qodem BEGIN marker" $?
KNAME=$(uname)
grep -q "$KNAME" "$OUT/cap.txt"
ok "capture file contains the executed command output ($KNAME)" $?

echo "CHECKS=$CHECKS FAILURES=$FAILURES"
if [ "$FAILURES" -ne 0 ]; then
    echo "--- session output ---"
    cat "$OUT/session.txt"
    exit 1
fi
exit 0
