#!/bin/bash
# test.sh — consumer contract tests for the ydotool CLI package (R34/PF3/L0c).
#
# Invoked by test_package/conanfile.py with:
#   YDOTOOL_BIN=<package bin/ydotool> YDOTOOLD_BIN=<package bin/ydotoold>
#   MOCK_DAEMON=<built userspace AF_UNIX peer> bash test.sh
#
# Assertions (16 designed):
#   A1-A6  CLI contract: help lists the command set / unknown command rc=1 /
#          ydotoold --version reports the packaged version / ydotoold --help /
#          missing socket rc=2 + daemon hint / non-socket path rc=2
#   A7     packaged artifacts: bin/ydotool and bin/ydotoold exist and are ELF
#   A8     platform capability probe: the mock daemon either binds its AF_UNIX
#          socket ("LISTENING") or documents the E024 limitation (OHOS SELinux
#          denies AF_UNIX bind() with EPERM on every writable filesystem)
#   A9-A15 Wire protocol via the mock daemon: exact input_event byte streams
#          for key / click / mousemove (relative + absolute INT32_MIN sync
#          convention) / type (lowercase + shift-wrapped uppercase). These run
#          wherever AF_UNIX pathname sockets are permitted; on E024-restricted
#          HarmonyOS they are reported as skipped (not failed), with the
#          platform reason, exactly like the upstream tests of other OHOS
#          packages that need Unix domain sockets.
#   A16    Real ydotoold platform behaviour: starts and accepts a client event
#          when /dev/uinput is accessible, or exits 2 with "failed to open
#          uinput device" when the platform blocks it (HarmonyOS PC grants
#          ordinary user processes EACCES on /dev/uinput)
# Deliberately no `set -e`: each assertion captures its own command status
# and all of them are reported in a single run.
set -u

: "${YDOTOOL_BIN:?YDOTOOL_BIN not set}"
: "${YDOTOOLD_BIN:?YDOTOOLD_BIN not set}"
: "${MOCK_DAEMON:?MOCK_DAEMON not set}"

CHECKS=0
FAILS=0
SKIPPED=0

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

WORK="./ydotool-test-$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

SOCK="$WORK/daemon.sock"

# --- A1: help lists the command set -----------------------------------------
A1_RC=0
A1_OUT="$("$YDOTOOL_BIN" help 2>&1)" || A1_RC=$?
if [ "$A1_RC" -eq 0 ] \
   && echo "$A1_OUT" | grep -q "Available commands:" \
   && echo "$A1_OUT" | grep -q "click" \
   && echo "$A1_OUT" | grep -q "mousemove" \
   && echo "$A1_OUT" | grep -q "type" \
   && echo "$A1_OUT" | grep -q "key"; then RC=0; else RC=1; fi
check "A1 ydotool help lists the command set (rc=$A1_RC)" $RC

# --- A2: unknown command -> rc 1 + message ----------------------------------
A2_RC=0
A2_OUT="$("$YDOTOOL_BIN" definitely-not-a-command 2>&1)" || A2_RC=$?
if [ "$A2_RC" -eq 1 ] && echo "$A2_OUT" | grep -q "Unknown command"; then RC=0; else RC=1; fi
check "A2 unknown command exits 1 with a message (rc=$A2_RC)" $RC

# --- A3: packaged daemon reports the packaged version (patch 0001) ----------
A3_RC=0
A3_OUT="$("$YDOTOOLD_BIN" --version 2>&1)" || A3_RC=$?
if [ "$A3_RC" -eq 0 ] && [ "$A3_OUT" = "1.0.4" ]; then RC=0; else RC=1; fi
check "A3 ydotoold --version reports 1.0.4 (got: ${A3_OUT:-<empty>})" $RC

# --- A4: ydotoold --help -> rc 0 + usage ------------------------------------
A4_RC=0
A4_OUT="$("$YDOTOOLD_BIN" --help 2>&1)" || A4_RC=$?
if [ "$A4_RC" -eq 0 ] && echo "$A4_OUT" | grep -q "Usage: ydotoold"; then RC=0; else RC=1; fi
check "A4 ydotoold --help exits 0 with usage (rc=$A4_RC)" $RC

# --- A5: missing socket -> rc 2 + daemon hint -------------------------------
A5_RC=0
A5_OUT="$(YDOTOOL_SOCKET="$WORK/does-not-exist.sock" "$YDOTOOL_BIN" key 1:1 2>&1)" || A5_RC=$?
if [ "$A5_RC" -eq 2 ] \
   && echo "$A5_OUT" | grep -q "failed to connect socket" \
   && echo "$A5_OUT" | grep -q "Please check if ydotoold is running"; then RC=0; else RC=1; fi
check "A5 missing socket exits 2 with the daemon hint (rc=$A5_RC)" $RC

# --- A6: non-socket path -> rc 2 (negative control) -------------------------
: > "$WORK/not-a-socket"
A6_RC=0
A6_OUT="$(YDOTOOL_SOCKET="$WORK/not-a-socket" "$YDOTOOL_BIN" key 1:1 2>&1)" || A6_RC=$?
if [ "$A6_RC" -eq 2 ] && echo "$A6_OUT" | grep -q "failed to connect socket"; then RC=0; else RC=1; fi
check "A6 non-socket path exits 2 with a connect error (rc=$A6_RC)" $RC

# --- A7: packaged artifacts exist and are ELF -------------------------------
A7_RC=0
for B in "$YDOTOOL_BIN" "$YDOTOOLD_BIN"; do
    if [ -x "$B" ] && [ "$(head -c 4 "$B" | od -An -tx1 | tr -d ' \n')" = "7f454c46" ]; then
        :
    else
        A7_RC=1
    fi
done
check "A7 bin/ydotool and bin/ydotoold are executable ELF binaries" $A7_RC

# --- A8: AF_UNIX capability of the platform (gates A9-A15) ------------------
rm -f "$SOCK"
: > "$WORK/mock0.out"
"$MOCK_DAEMON" "$SOCK" 0 > "$WORK/mock0.out" 2>&1 &
M0=$!
M0_RC=0
wait "$M0" 2>/dev/null || M0_RC=$?
BIND_OK=0
if grep -q "LISTENING" "$WORK/mock0.out" 2>/dev/null && [ "$M0_RC" -eq 0 ]; then
    BIND_OK=1
    RC=0
elif grep -q "BIND-FAILED errno=1 " "$WORK/mock0.out" 2>/dev/null; then
    RC=0   # E024: documented HarmonyOS platform limitation, not a product defect
else
    RC=1
fi
if [ "$BIND_OK" -eq 1 ]; then
    check "A8 mock daemon binds its AF_UNIX socket and reports LISTENING" $RC
else
    check "A8 platform AF_UNIX probe: bind() denied with EPERM (E024 limitation documented)" $RC
fi

# --- Wire-protocol assertions (require AF_UNIX pathname sockets) ------------
# run_client_expect <description> <expected-count> <expected-lines-file> <args...>
run_client_expect() {
    DESC="$1"; CNT="$2"; EXP="$3"; shift 3
    rm -f "$SOCK"
    : > "$WORK/mock.out"
    "$MOCK_DAEMON" "$SOCK" "$CNT" > "$WORK/mock.out" 2>&1 &
    MPID=$!
    WAITED=0
    while [ "$WAITED" -lt 5 ] && ! grep -q "LISTENING" "$WORK/mock.out" 2>/dev/null; do
        sleep 1
        WAITED=$((WAITED + 1))
        kill -0 "$MPID" 2>/dev/null || break
    done
    CLI_RC=0
    YDOTOOL_SOCKET="$SOCK" "$YDOTOOL_BIN" "$@" > "$WORK/cli.out" 2>&1 || CLI_RC=$?
    MOCK_RC=0
    wait "$MPID" 2>/dev/null || MOCK_RC=$?
    sed -n 's/^EV [0-9]* //p' "$WORK/mock.out" > "$WORK/mock.events"
    if [ "$CLI_RC" -eq 0 ] && [ "$MOCK_RC" -eq 0 ] \
       && diff -u "$EXP" "$WORK/mock.events" > /dev/null 2>&1; then REST=0; else REST=1; fi
    if [ "$REST" -ne 0 ]; then
        echo "    cli_rc=$CLI_RC mock_rc=$MOCK_RC" >&2
        diff -u "$EXP" "$WORK/mock.events" >&2 || true  # diagnostic only; assert result is REST
        sed -n '1,5p' "$WORK/cli.out" >&2
    fi
    check "$DESC" $REST
}

if [ "$BIND_OK" -eq 1 ]; then
    # --- A9: `key 1:1` -> key down + SYN ------------------------------------
    cat > "$WORK/exp_key_down.txt" <<'EOF'
type=1 code=1 value=1
type=0 code=0 value=0
EOF
    run_client_expect "A9 key 1:1 emits EV_KEY/1/1 + SYN_REPORT" 2 "$WORK/exp_key_down.txt" key 1:1

    # --- A10: full press/release pair ----------------------------------------
    cat > "$WORK/exp_key_pair.txt" <<'EOF'
type=1 code=30 value=1
type=0 code=0 value=0
type=1 code=30 value=0
type=0 code=0 value=0
EOF
    run_client_expect "A10 key 30:1 30:0 emits down+up each followed by SYN" 4 "$WORK/exp_key_pair.txt" key 30:1 30:0

    # --- A11: left click -> BTN_LEFT (0x110) down+up -------------------------
    cat > "$WORK/exp_click.txt" <<'EOF'
type=1 code=272 value=1
type=0 code=0 value=0
type=1 code=272 value=0
type=0 code=0 value=0
EOF
    run_client_expect "A11 click 0xC0 emits BTN_LEFT down+up with SYN" 4 "$WORK/exp_click.txt" click 0xC0

    # --- A12: relative mousemove ---------------------------------------------
    cat > "$WORK/exp_mousemove.txt" <<'EOF'
type=2 code=0 value=-100
type=2 code=1 value=100
type=0 code=0 value=0
EOF
    run_client_expect "A12 mousemove -x -100 -y 100 emits REL_X/REL_Y + SYN" 3 "$WORK/exp_mousemove.txt" mousemove -x -100 -y 100

    # --- A13: absolute mousemove uses the INT32_MIN sync markers -------------
    cat > "$WORK/exp_mousemove_abs.txt" <<'EOF'
type=2 code=0 value=-2147483648
type=2 code=1 value=-2147483648
type=0 code=0 value=0
type=2 code=0 value=0
type=2 code=1 value=0
type=0 code=0 value=0
EOF
    run_client_expect "A13 mousemove --absolute emits INT32_MIN sync markers then the position" 6 "$WORK/exp_mousemove_abs.txt" mousemove --absolute -x 0 -y 0

    # --- A14: type a -> KEY_A (30) down+up -----------------------------------
    cat > "$WORK/exp_type_a.txt" <<'EOF'
type=1 code=30 value=1
type=0 code=0 value=0
type=1 code=30 value=0
type=0 code=0 value=0
EOF
    run_client_expect "A14 type a emits KEY_A down+up" 4 "$WORK/exp_type_a.txt" type -H 0 -d 0 a

    # --- A15: type A -> LEFTSHIFT-wrapped KEY_A ------------------------------
    cat > "$WORK/exp_type_A.txt" <<'EOF'
type=1 code=42 value=1
type=0 code=0 value=0
type=1 code=30 value=1
type=0 code=0 value=0
type=1 code=30 value=0
type=0 code=0 value=0
type=1 code=42 value=0
type=0 code=0 value=0
EOF
    run_client_expect "A15 type A wraps KEY_A with LEFTSHIFT (42)" 8 "$WORK/exp_type_A.txt" type -H 0 -d 0 A
else
    echo "  [SKIP] A9-A15: E024 — HarmonyOS SELinux denies AF_UNIX bind() (EPERM)," >&2
    echo "         so the wire-protocol byte assertions cannot run on this platform" >&2
    SKIPPED=$((SKIPPED + 7))
fi

# --- A16: real daemon vs /dev/uinput (platform boundary) --------------------
DAEMON_SOCK="$WORK/real-daemon.sock"
rm -f "$DAEMON_SOCK"
"$YDOTOOLD_BIN" -p "$DAEMON_SOCK" -P 0600 > "$WORK/daemon.out" 2> "$WORK/daemon.err" &
DPID=$!
sleep 1
if kill -0 "$DPID" 2>/dev/null; then
    # uinput is accessible: the daemon must become READY and relay an event.
    WAITED=0
    while [ "$WAITED" -lt 5 ] && ! grep -q "READY" "$WORK/daemon.out" 2>/dev/null; do
        sleep 1
        WAITED=$((WAITED + 1))
    done
    D_RC=0
    YDOTOOL_SOCKET="$DAEMON_SOCK" "$YDOTOOL_BIN" key 1:1 > "$WORK/real-cli.out" 2>&1 || D_RC=$?
    # stop the daemon; its exit status is not part of this assertion
    kill "$DPID" 2>/dev/null || true
    wait "$DPID" 2>/dev/null || true
    if [ "$D_RC" -eq 0 ] && grep -q "READY" "$WORK/daemon.out"; then RC=0; else RC=1; fi
    check "A16 real ydotoold READY and relaying client events (uinput accessible, rc=$D_RC)" $RC
else
    # uinput is blocked: the daemon must fail fast with the documented error.
    D_RC=0
    wait "$DPID" 2>/dev/null || D_RC=$?
    if [ "$D_RC" -eq 2 ] && grep -q "failed to open uinput device" "$WORK/daemon.err"; then RC=0; else RC=1; fi
    check "A16 real ydotoold exits 2 with 'failed to open uinput device' when uinput is blocked (rc=$D_RC)" $RC
fi

if [ "$SKIPPED" -gt 0 ]; then
    echo "test_ydotool: $((CHECKS - FAILS))/${CHECKS} executed assertions passed (${SKIPPED} skipped: E024 AF_UNIX bind EPERM)"
else
    echo "test_ydotool: $((CHECKS - FAILS))/${CHECKS} assertions passed"
fi
if [ "$FAILS" -ne 0 ]; then
    echo "test_ydotool: FAILED" >&2
    exit 1
fi
echo "test_ydotool: ALL TESTS PASSED"
