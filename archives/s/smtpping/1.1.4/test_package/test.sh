#!/bin/sh
# test.sh — consumer E2E for the smtpping CLI package (R34/PF3/L0c).
#
# Invoked by test_package/conanfile.py with:
#   SMTPPING_BIN=<package bin/smtpping> MOCK_SMTP=<built mock server> bash test.sh
#
# Assertions (15):
#   A1-A4  CLI contract: executable / -v reports 1.1.4 / no-arg usage rc=2 /
#          -h usage rc=0
#   A5-A13 Loopback E2E: mock SMTP server listens; smtpping probe exits 0;
#          statistics report 1 transmitted message + header; transcript
#          contains HELO / MAIL FROM / RCPT TO / QUIT; mock server exits 0
#   A14-A15 Negative controls: closed port -> connect() failed + no pings
#          sent; MX->A/AAAA resolver fallback path completes without crash
set -eu

: "${SMTPPING_BIN:?SMTPPING_BIN not set}"
: "${MOCK_SMTP:?MOCK_SMTP not set}"

CHECKS=0
FAILS=0

check() {
    # $1 = description, $2 = 0 (pass) / non-zero (fail)
    CHECKS=$((CHECKS + 1))
    if [ "$2" -eq 0 ]; then
        echo "  [PASS] $1"
    else
        echo "  [FAIL] $1" >&2
        FAILS=$((FAILS + 1))
    fi
}

WORK="./smtpping-test-$$"
mkdir -p "$WORK"

# --- A1: binary present and executable -------------------------------------
if [ -x "$SMTPPING_BIN" ]; then RC=0; else RC=1; fi
check "A1 binary present and executable: $SMTPPING_BIN" $RC

# --- A2: -v reports the packaged version -----------------------------------
V_OUT="$("$SMTPPING_BIN" -v 2>&1 || true)"
case "$V_OUT" in
    *1.1.4*) RC=0 ;;
    *) RC=1 ;;
esac
check "A2 smtpping -v reports 1.1.4 (got: ${V_OUT:-<empty>})" $RC

# --- A3: no arguments -> usage on stderr, exit 2 ---------------------------
N_RC=0
N_ERR="$("$SMTPPING_BIN" 2>&1 >"$WORK/noargs.out")" || N_RC=$?
if [ "$N_RC" -eq 2 ] && echo "$N_ERR" | grep -q "Usage: smtpping"; then RC=0; else RC=1; fi
check "A3 no-argument invocation exits 2 with usage on stderr (rc=$N_RC)" $RC

# --- A4: -h -> usage on stdout, exit 0 -------------------------------------
H_RC=0
H_OUT="$("$SMTPPING_BIN" -h 2>"$WORK/help.err")" || H_RC=$?
if [ "$H_RC" -eq 0 ] && echo "$H_OUT" | grep -q "Usage: smtpping"; then RC=0; else RC=1; fi
check "A4 smtpping -h exits 0 with usage (rc=$H_RC)" $RC

# --- A5: start the mock SMTP server on a free-ish port ---------------------
PORT=$((20000 + ($$ % 20000)))
SERVER_OUT="$WORK/server.out"
TRANSCRIPT="$WORK/transcript.txt"
SERVER_PID=""
TRIES=0
while [ "$TRIES" -lt 5 ]; do
    : > "$SERVER_OUT"
    "$MOCK_SMTP" "$PORT" "$TRANSCRIPT" >"$SERVER_OUT" 2>&1 &
    SERVER_PID=$!
    WAITED=0
    while [ "$WAITED" -lt 30 ] && [ ! -s "$SERVER_OUT" ]; do
        sleep 1
        WAITED=$((WAITED + 1))
        kill -0 "$SERVER_PID" 2>/dev/null || break
    done
    if grep -q "LISTENING" "$SERVER_OUT" 2>/dev/null; then
        break
    fi
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
    SERVER_PID=""
    PORT=$((PORT + 1))
    TRIES=$((TRIES + 1))
done
if [ -n "$SERVER_PID" ] && grep -q "LISTENING" "$SERVER_OUT" 2>/dev/null; then RC=0; else RC=1; fi
check "A5 mock SMTP server listening on 127.0.0.1:$PORT" $RC

if [ -z "$SERVER_PID" ]; then
    echo "test_smtpping: cannot continue without the mock server" >&2
    echo "test_smtpping: $((CHECKS - FAILS))/${CHECKS} assertions passed" >&2
    exit 1
fi

# --- A6-A12: full probe against the mock server ----------------------------
PING_RC=0
PING_OUT="$("$SMTPPING_BIN" -p "$PORT" -c 1 -w 0 test@localhost @127.0.0.1 2>"$WORK/ping.err")" || PING_RC=$?
SRV_RC=0
wait "$SERVER_PID" 2>/dev/null || SRV_RC=$?

if [ "$PING_RC" -eq 0 ]; then RC=0; else RC=1; fi
check "A6 smtpping probe against mock server exits 0 (rc=$PING_RC)" $RC

if echo "$PING_OUT" | grep -q "1 e-mail messages transmitted"; then RC=0; else RC=1; fi
check "A7 statistics report 1 transmitted message" $RC

if echo "$PING_OUT" | grep -q "SMTP ping statistics"; then RC=0; else RC=1; fi
check "A8 statistics header present" $RC

for TOKEN in "HELO " "MAIL FROM:" "RCPT TO:" "QUIT"; do
    if grep -q "$TOKEN" "$TRANSCRIPT" 2>/dev/null; then RC=0; else RC=1; fi
    check "A9-A12 transcript contains '$TOKEN'" $RC
done

if [ "$SRV_RC" -eq 0 ]; then RC=0; else RC=1; fi
check "A13 mock server completed the session and exited 0 (rc=$SRV_RC)" $RC

# --- A14: closed port negative control (port 1 on loopback is never open) --
NEG_RC=0
NEG_OUT="$("$SMTPPING_BIN" -p 1 -c 1 -w 0 test@localhost @127.0.0.1 2>"$WORK/neg.err")" || NEG_RC=$?
NEG_ERR="$(cat "$WORK/neg.err")"
if [ "$NEG_RC" -eq 0 ] && echo "$NEG_OUT" | grep -q "no pings were sent" && echo "$NEG_ERR" | grep -q "connect() failed"; then
    RC=0
else
    RC=1
fi
check "A14 closed-port negative control: rc=$NEG_RC, connect() failed + no pings sent" $RC

# --- A15: resolver path (MX -> A/AAAA fallback) does not crash -------------
RES_RC=0
RES_OUT="$("$SMTPPING_BIN" -c 1 -w 0 test@localhost 2>"$WORK/res.err")" || RES_RC=$?
RES_ERR="$(cat "$WORK/res.err")"
if [ "$RES_RC" -eq 0 ] && { echo "$RES_OUT" | grep -q "no pings were sent" || echo "$RES_ERR" | grep -q "failed to resolve"; }; then
    RC=0
else
    RC=1
fi
check "A15 resolver fallback path completes without crash (rc=$RES_RC)" $RC

echo "test_smtpping: $((CHECKS - FAILS))/${CHECKS} assertions passed"
if [ "$FAILS" -ne 0 ]; then
    echo "test_smtpping: FAILED" >&2
    exit 1
fi
echo "test_smtpping: ALL TESTS PASSED"
