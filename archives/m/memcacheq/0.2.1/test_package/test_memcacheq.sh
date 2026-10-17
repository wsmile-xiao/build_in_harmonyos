#!/bin/sh
# Functional test-suite for the packaged memcacheq 0.2.1 binary.
#
# Runs against a real memcacheq daemon started from the Conan package on a
# HarmonyOS (or Linux) host.  Everything speaks the plain-text memcache
# protocol over TCP, so the only dependency is a POSIX shell + dd/nc-style
# I/O done with pure shell builtins and dd.
#
# Usage: test_memcacheq.sh <bindir-of-package>
#
# Exit code 0 = all cases passed, 1 = at least one failure.

set -u

BIN_DIR="${1:-.}"
BIN="$BIN_DIR/memcacheq"
WORK=""

pass=0
fail=0
FAILED_CASES=""

say() { printf '%s\n' "$*"; }

ok() {
    pass=$((pass + 1))
    say "ok $pass - $1"
}

not_ok() {
    fail=$((fail + 1))
    FAILED_CASES="$FAILED_CASES $1"
    say "not ok $pass - $1"
    [ $# -gt 1 ] && say "# $2"
}

# assert_eq <name> <expected> <actual>
assert_eq() {
    if [ "$2" = "$3" ]; then
        ok "$1"
    else
        not_ok "$1" "expected: [$2], got: [$3]"
    fi
}

# send_recv <port> <payload-with-\r\n>  -- reads the reply's first line
# The reply is terminated by the connection being closed by the server-side
# timeout (-q 1: quit 1s after EOF on stdin) or by netcat's own -w timeout.
send_recv() {
    _port="$1"; _payload="$2"
    _reply="$( (printf '%b' "$_payload") | netcat -w 3 -q 1 127.0.0.1 "$_port" 2>/dev/null | head -n 1 | tr -d '\r\n' )"
    [ -z "$_reply" ] && _reply="(no reply)"
    printf '%s' "$_reply"
}

# port_open <port> -- true when something accepts a TCP connection there.
# No `nc -z` on toybox netcat: use a zero-length write attempt instead.
port_open() {
    _p="$1"
    (printf '' | netcat -w 2 -q 1 127.0.0.1 "$_p") >/dev/null 2>&1 && return 0
    # A refused/failed connection makes netcat exit non-zero; but a server
    # that accepts and immediately waits gives exit 0 on EOF-quit.  Some
    # netcat builds exit 1 on timeout even when connected -- fall back to a
    # protocol probe: a version command must yield a reply.
    _r="$( (printf 'version\r\n') | netcat -w 2 -q 1 127.0.0.1 "$_p" 2>/dev/null | head -n 1 )"
    [ -n "$_r" ]
}

cleanup() {
    if [ -n "${MQ_PID:-}" ] && kill -0 "$MQ_PID" 2>/dev/null; then
        kill "$MQ_PID" 2>/dev/null
        wait "$MQ_PID" 2>/dev/null
    fi
    [ -n "$WORK" ] && rm -rf "$WORK"
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------- start up
if [ ! -x "$BIN" ]; then
    say "BAIL OUT! memcacheq binary not found or not executable: $BIN"
    exit 1
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/mcq.XXXXXX")"
PORT=$(( (RANDOM % 2000) + 22000 ))
DB_HOME="$WORK/dbhome"
mkdir -p "$DB_HOME"

"$BIN" -p "$PORT" -H "$DB_HOME" -N -R -v > "$WORK/server.log" 2>&1 &
MQ_PID=$!

# Wait for the port to accept connections (up to ~10s).
_i=0
while [ $_i -lt 40 ]; do
    if port_open "$PORT"; then
        break
    fi
    if ! kill -0 "$MQ_PID" 2>/dev/null; then
        say "BAIL OUT! memcacheq exited early; log:"
        sed -n '1,30p' "$WORK/server.log"
        exit 1
    fi
    sleep 0.25
    _i=$((_i + 1))
done

if ! port_open "$PORT"; then
    say "BAIL OUT! memcacheq did not start listening on $PORT; log:"
    sed -n '1,30p' "$WORK/server.log"
    exit 1
fi

# ------------------------------------------------------------- test cases

# F1: version command
assert_eq "F1 version command returns VERSION 0.2.1" \
    "VERSION 0.2.1" "$(send_recv "$PORT" 'version\r\n')"

# F2: set a message into a named queue, expect STORED
assert_eq "F2 set stores a message" \
    "STORED" "$(send_recv "$PORT" 'set myqueue 0 0 5\r\nhello\r\n')"

# F3: get pops the message (FIFO queue semantics: set-then-get)
assert_eq "F3 get pops the queued message body" \
    "VALUE myqueue 0 5" "$(send_recv "$PORT" 'get myqueue\r\n')"

# F4: queue drained: second get must be END
assert_eq "F4 empty queue returns END" \
    "END" "$(send_recv "$PORT" 'get myqueue\r\n')"

# F5: FIFO ordering across two messages
send_recv "$PORT" 'set q2 0 0 3\r\nfoo\r\n' > /dev/null
send_recv "$PORT" 'set q2 0 0 3\r\nbar\r\n' > /dev/null
_r1="$(send_recv "$PORT" 'get q2\r\n')"
assert_eq "F5 first get from q2 returns first message (foo)" \
    "VALUE q2 0 3" "$_r1"
assert_eq "F5b second get from q2 returns second message (bar)" \
    "VALUE q2 0 3" "$(send_recv "$PORT" 'get q2\r\n')"

# F6: stats shows process statistics
_r="$(send_recv "$PORT" 'stats\r\n')"
case "$_r" in
    "STAT pid "*) ok "F6 stats reports STAT pid";;
    *) not_ok "F6 stats reports STAT pid" "got: [$_r]";;
esac

# F7: stats queue shows per-queue counters
_r="$(send_recv "$PORT" 'stats queue\r\n')"
case "$_r" in
    "STAT "*) ok "F7 stats queue reports STAT lines";;
    *) not_ok "F7 stats queue reports STAT lines" "got: [$_r]";;
esac

# F8: delete an empty (nonexistent) queue -> NOT_FOUND
assert_eq "F8 delete nonexistent queue returns NOT_FOUND" \
    "NOT_FOUND" "$(send_recv "$PORT" 'delete nosuchq\r\n')"

# F9: unknown command -> ERROR
assert_eq "F9 unknown command returns ERROR" \
    "ERROR" "$(send_recv "$PORT" 'boguscommand\r\n')"

# F10: message larger than one byte, verify length echo in VALUE line
send_recv "$PORT" 'set bigq 0 0 11\r\nhello world\r\n' > /dev/null
assert_eq "F10 VALUE header carries correct byte length" \
    "VALUE bigq 0 11" "$(send_recv "$PORT" 'get bigq\r\n')"

# F11: separate queues do not interfere
send_recv "$PORT" 'set qa 0 0 2\r\nAA\r\n' > /dev/null
send_recv "$PORT" 'set qb 0 0 2\r\nBB\r\n' > /dev/null
_r="$(send_recv "$PORT" 'get qa\r\n')"
case "$_r" in
    "VALUE qa 0 2") ok "F11 queue isolation (qa returns its own message)";;
    *) not_ok "F11 queue isolation (qa returns its own message)" "got: [$_r]";;
esac
_r="$(send_recv "$PORT" 'get qb\r\n')"
case "$_r" in
    "VALUE qb 0 2") ok "F11b queue isolation (qb returns its own message)";;
    *) not_ok "F11b queue isolation (qb returns its own message)" "got: [$_r]";;
esac

# F12: usage / help text on stdout, exit 0
if "$BIN" -h > "$WORK/usage.txt" 2>&1 && grep -q "TCP port number to listen on" "$WORK/usage.txt"; then
    ok "F12 -h prints usage mentioning the port option"
else
    not_ok "F12 -h prints usage mentioning the port option"
fi

# F13: usage_license on stdout
if "$BIN" -i > "$WORK/license.txt" 2>&1 && grep -q "Steve Chu" "$WORK/license.txt"; then
    ok "F13 -i prints the BSD license text"
else
    not_ok "F13 -i prints the BSD license text"
fi

# ---------------------------------------------------------------- summary
TOTAL=$((pass + fail))
say ""
say "# total=$TOTAL passed=$pass failed=$fail"
if [ "$fail" -gt 0 ]; then
    say "# failed cases:$FAILED_CASES"
    say "# server log tail:"
    tail -n 20 "$WORK/server.log" 2>/dev/null | sed 's/^/#   /'
    exit 1
fi
exit 0
