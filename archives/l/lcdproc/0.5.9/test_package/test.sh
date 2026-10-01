#!/bin/sh
# test_package/test.sh - consumer test for the packaged lcdproc 0.5.9 suite.
#
# Usage: test.sh <bindir> <driverdir> <lcdd_stub.py>
#
# lcdproc 0.5.9 ships no library (shared/Makefile.am declares libLCDstuff.a
# `noinst_LIBRARIES`), so the consumer-visible surface is the executable suite:
# the LCDd daemon, its driver plugins, and the three clients.  Every case below
# therefore executes a real packaged binary and asserts on what it really
# prints / returns - no echo-only shells.
#
# Case 6 drives the packaged client through a complete live LCDd session; the
# peer at the other end of the socket is the fixture <lcdd_stub.py>, which is a
# test helper and is not part of the package payload.
#
# /tmp is read-only on OHOS, so the scratch tree lives under $HOME.

set -eu

BIN="$1"
DRV="$2"

SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/lcdproc-test-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT INT TERM

# ELF e_machine of an AArch64 object is 0xB7, little endian, i.e. the two bytes
# b7 00 - compared here after squeezing the separators out of od's output.
# This is the OHOS/HarmonyOS PC target architecture: the adaptation's whole
# point is that every artifact is a native aarch64 OHOS binary.
AARCH64_MACHINE="b700"

# Read $2 hex bytes at offset $3 of file $1, as lowercase hex with no spaces.
# `od` is used when present; the OHOS CI worker is not guaranteed to ship it, and
# a hard dependency on it would turn cases 6/7 into a *tooling* test rather than
# an *ABI* test.  conan itself is a Python program, so python3 is always there.
elf_hex() {
    _f="$1"; _len="$2"; _off="$3"
    if command -v od >/dev/null 2>&1; then
        od -An -tx1 -j "$_off" -N "$_len" "$_f" | tr -d ' \n'
    else
        python3 -c 'import sys
p,off,ln=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
with open(p,"rb") as f:
    f.seek(off)
    sys.stdout.write("".join("%02x"%b for b in f.read(ln)))' "$_f" "$_off" "$_len"
    fi
}

n_pass=0

pass() {
    n_pass=$((n_pass + 1))
    echo "PASS: $1"
}

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

# Run a command under a watchdog; OHOS /system/bin/sh is mksh and has no
# `timeout`, so the guard is built from background + sleep + kill.
# Returns the child's real exit status; 124 means the watchdog fired.
run_guarded() {
    _secs="$1"; shift
    "$@" > "$TESTDIR/out" 2>&1 &
    _pid=$!
    _i=0
    while [ "$_i" -lt "$_secs" ]; do
        kill -0 "$_pid" 2>/dev/null || break
        sleep 1
        _i=$((_i + 1))
    done
    if kill -0 "$_pid" 2>/dev/null; then
        kill -9 "$_pid" 2>/dev/null || true
        wait "$_pid" 2>/dev/null || true
        return 124
    fi
    wait "$_pid" 2>/dev/null
}

# Assert the file at $1 is an AArch64 ELF (magic 7f454c46, class 64-bit,
# little endian, e_machine == 0xB7).
assert_aarch64_elf() {
    _f="$1"
    _what="$2"
    [ -f "$_f" ] || fail "$_what: missing file $_f"
    _magic=$(elf_hex "$_f" 4 0)
    [ "$_magic" = "7f454c46" ] || fail "$_what: not an ELF ($_magic)"
    _mach=$(elf_hex "$_f" 2 18)
    [ "$_mach" = "$AARCH64_MACHINE" ] \
        || fail "$_what: e_machine=$_mach, expected $AARCH64_MACHINE (AArch64)"
}

# --------------------------------------------------------------- 1. lcdproc -h
# The client's own getopt usage screen; upstream takes -h only (--help is
# parsed as separate short options and is rejected), so the case pins that.
run_guarded 20 "$BIN/lcdproc" -h || fail "lcdproc -h did not exit cleanly (rc=$?)"
[ "$(cat "$TESTDIR/out")" ] || fail "lcdproc -h printed nothing"
grep -q "lcdproc - LCDproc system status information viewer" "$TESTDIR/out" \
    || fail "lcdproc -h lacks its banner"
grep -q "Usage: lcdproc" "$TESTDIR/out" || fail "lcdproc -h lacks usage line"
grep -q -- "-s <host>" "$TESTDIR/out" || fail "lcdproc -h lacks the -s option doc"
grep -q -- "-p <port>" "$TESTDIR/out" || fail "lcdproc -h lacks the -p option doc"
pass "lcdproc -h prints its full usage screen"

# --------------------------------------------------------------- 2. lcdexec -h
run_guarded 20 "$BIN/lcdexec" -h || fail "lcdexec -h did not exit cleanly (rc=$?)"
grep -q "lcdexec - LCDproc client to execute commands from the LCDd menu" "$TESTDIR/out" \
    || fail "lcdexec -h lacks its banner"
grep -q "Usage: lcdexec" "$TESTDIR/out" || fail "lcdexec -h lacks usage line"
grep -q -- "-p <port>" "$TESTDIR/out" || fail "lcdexec -h lacks the -p option doc"
pass "lcdexec -h prints its full usage screen"

# ---------------------------------------------------------------- 3. lcdvc -h
run_guarded 20 "$BIN/lcdvc" -h || fail "lcdvc -h did not exit cleanly (rc=$?)"
grep -q "lcdvc - LCDproc virtual console" "$TESTDIR/out" \
    || fail "lcdvc -h lacks its banner"
grep -q "Usage: lcdvc" "$TESTDIR/out" || fail "lcdvc -h lacks usage line"
pass "lcdvc -h prints its full usage screen"

# ------------------------------------------- 4. lcdproc against a dead LCDd
# Exercises the real client code path (sockets.c -> sock_connect) rather than
# just the usage screen: a refused TCP connect must be reported verbatim.
PORT=39117
rc=0
run_guarded 25 "$BIN/lcdproc" -s 127.0.0.1 -p "$PORT" -f || rc=$?
[ "$rc" -ne 124 ] || fail "lcdproc hung instead of failing fast"
[ "$rc" -eq 1 ] || fail "lcdproc exit status is $rc, expected 1 on a refused connect"
grep -q "Error connecting to LCD server 127.0.0.1 on port $PORT." "$TESTDIR/out" \
    || { cat "$TESTDIR/out" >&2; fail "lcdproc did not report the refused connection"; }
grep -q "Check to see that the server is running" "$TESTDIR/out" \
    || fail "lcdproc did not print the 'server is running' hint"
pass "lcdproc reports a refused LCDd connection (port $PORT)"

# ------------------------------------------- 5. lcdvc on a machine with no LCDd
# lcdvc is the *virtual console* client, so its first real action is opening
# /dev/vcs and reading its config file; only after that does it try to reach
# LCDd.  Which of the two you see therefore depends on the machine:
#   * a build host that has /dev/vcs  -> it reaches sock_connect and reports
#     "Connecting to 127.0.0.1:39117 failed"
#   * a device without /dev/vcs (real OHOS hardware) -> it aborts one step
#     earlier with "Could not open /dev/vcs: No such file or directory"
# Both are genuine runtime paths of the shipped binary.  Asserting only the
# first one (as an earlier revision of this file did) made the case a platform
# assumption rather than a fact - it passed locally and failed on CI #64338.
# What IS invariant is: the binary really runs, reaches its error path, emits a
# real diagnostic, and exits 255.  The connect path itself is still covered
# unconditionally by case 4 (lcdproc), which has no /dev/vcs dependency.
rc=0
run_guarded 25 "$BIN/lcdvc" -a 127.0.0.1 -p "$PORT" -f || rc=$?
[ "$rc" -ne 124 ] || fail "lcdvc hung instead of failing fast"
[ "$rc" -eq 255 ] || fail "lcdvc exit status is $rc, expected 255 (Critical error, abort)"
[ -s "$TESTDIR/out" ] || fail "lcdvc printed nothing at all"
grep -q "Critical error, abort" "$TESTDIR/out" \
    || { cat "$TESTDIR/out" >&2; fail "lcdvc did not abort on its way out"; }
if grep -q "Connecting to 127.0.0.1:$PORT failed" "$TESTDIR/out"; then
    :
elif grep -q "/dev/vcs" "$TESTDIR/out"; then
    # no console device on this host - a real device, not a broken package
    :
else
    cat "$TESTDIR/out" >&2
    fail "lcdvc reported neither the refused connection nor the missing console device"
fi
pass "lcdvc runs on this host and aborts with a real diagnostic (rc=255)"

# ------------------------- 6. OHOS-specific: a complete live LCDd session
# Cases 1-5 only ever reach the client's *error* paths.  This one drives the
# packaged aarch64 OHOS client through the whole client/server flow that is the
# entire point of the suite:
#
#     TCP connect -> "hello" -> geometry negotiation -> screen_add/screen_set/
#     widget_add/widget_set carrying live data read from the running system ->
#     "bye" -> clean exit 0
#
# Every byte asserted below was put on the wire by the packaged binary; the peer
# on the other end is the small fixture lcdd_stub.py, which is not shipped.
# See lcdd_stub.py for why the real LCDd daemon cannot be the peer here.
#
# The geometry the peer negotiates (33x6) is deliberately not the client's
# built-in fallback (20x4, clients/lcdproc/main.c), so the echoed numbers are a
# hard proof that the handshake was parsed rather than defaulted.
STUB="$3"
[ -f "$STUB" ] || fail "missing LCDd protocol fixture: $STUB"
command -v python3 >/dev/null 2>&1 \
    || fail "python3 is required to run the LCDd protocol fixture"

STUB_PORTFILE="$TESTDIR/stub.port"
STUB_GREET="$TESTDIR/stub.greeting"
STUB_STREAM="$TESTDIR/stub.stream"
STUB_HOST="$TESTDIR/stub.host"

python3 "$STUB" "$STUB_PORTFILE" "$STUB_GREET" "$STUB_STREAM" "$STUB_HOST" 45 \
    > "$TESTDIR/stub.log" 2>&1 &
STUB_PID=$!

# Wait for the peer to publish its (kernel-assigned, ephemeral) port.
stub_port=""
stub_wait=0
while [ "$stub_wait" -lt 30 ]; do
    if [ -s "$STUB_PORTFILE" ]; then
        stub_port=$(cat "$STUB_PORTFILE")
        break
    fi
    kill -0 "$STUB_PID" 2>/dev/null || break
    sleep 1
    stub_wait=$((stub_wait + 1))
done
[ -n "$stub_port" ] || { cat "$TESTDIR/stub.log" >&2; fail "LCDd fixture never published a port"; }

# Only the CPU, Load and TimeDate screens: their widget_set lines are what the
# assertions below read, and asking for three screens keeps the session short
# and its captured stream deterministic.
rc=0
run_guarded 40 "$BIN/lcdproc" -s 127.0.0.1 -p "$stub_port" -f C T L || rc=$?
stub_rc=0
wait "$STUB_PID" 2>/dev/null || stub_rc=$?

[ -s "$STUB_STREAM" ] || { cat "$TESTDIR/stub.log" >&2; fail "LCDd fixture captured no client traffic"; }
[ "$stub_rc" -eq 0 ] || fail "LCDd fixture did not observe a complete session (rc=$stub_rc)"

# 6a. the client greeted the server the way upstream's server expects
grep -q '^hello$' "$STUB_GREET" \
    || { cat "$STUB_STREAM" >&2; fail "client did not send the 'hello' greeting"; }

# 6b. the client announced itself with the machine's real hostname.  This is a
#     cross-check against the live system, not a canned string: the fixture
#     reports socket.gethostname() and the client reports what it read itself.
stub_host=$(cat "$STUB_HOST")
client_name=$(grep '^client_set -name ' "$STUB_STREAM" | head -1 || true)
[ -n "$client_name" ] || fail "client never announced itself with client_set -name"
client_host=${client_name#client_set -name \{LCDproc }
client_host=${client_host%\}}
[ -n "$client_host" ] || fail "client announced an empty hostname"
[ "$client_host" = "$stub_host" ] \
    || fail "client announced hostname '$client_host' but the machine is '$stub_host'"

# 6c. the negotiated geometry came back on the wire.  A client that ignored the
#     connect line would emit the built-in 20x4 fallback here instead.
grep -q "^widget_set L zero 33 6 0$" "$STUB_STREAM" \
    || { cat "$STUB_STREAM" >&2; fail "client did not apply the negotiated 33x6 geometry"; }

# 6d. real screens were built and filled with live data read from this machine
for scr in C L T; do
    grep -q "^screen_add $scr$" "$STUB_STREAM" \
        || fail "client never created screen $scr"
done
# CPU gauge - literal row/col (cpu.c:163), value read from /proc/stat
grep -q '^widget_set C bar 3 4 [0-9][0-9]*$' "$STUB_STREAM" \
    || fail "client never populated the CPU load gauge from /proc/stat"
# Load histogram - bar19 is the 19th column, row 6 is the negotiated lcd_hgt
# (load.c:120), value read from /proc/loadavg
grep -q '^widget_set L bar19 19 6 [0-9][0-9]*$' "$STUB_STREAM" \
    || fail "client never populated the load histogram at the negotiated height"
# Time screen - the column is computed from lcd_wid (chrono.c:150), and the
# separators blink (tickTime blanks the colons on alternate heartbeats), so only
# the clock payload is asserted: a real wall-clock reading plus the idle figure
grep -q '^widget_set T three [0-9][0-9]* 4 {[0-9][0-9][: ][0-9][0-9][: ][0-9][0-9] [0-9][0-9]*% idle}$' "$STUB_STREAM" \
    || fail "client never populated the time screen from the live clock"
# Title bar - uname() system name + release (chrono.c:101)
grep -q '^widget_set T title {.*}$' "$STUB_STREAM" \
    || fail "client never built the time screen title from uname()"
grep -qF ": $stub_host}" "$STUB_STREAM" \
    || fail "client's title bar does not carry this machine's hostname"

# 6e. the peer said goodbye and the client shut down through the protocol
[ "$rc" -ne 124 ] || fail "lcdproc hung instead of honouring the 'bye' command"
[ "$rc" -eq 0 ] || fail "lcdproc exit status is $rc, expected 0 after the 'bye' command"
pass "packaged aarch64 OHOS client completed a full LCDd session (hello/handshake/${client_host}/33x6/3 screens/clean exit)"

# --------------------------------- 7. OHOS-specific: aarch64 OHOS ELF payloads
# The whole adaptation target is "HarmonyOS PC (OHOS aarch64)".  These four
# binaries are only reachable because the toolchain targeted aarch64-linux-ohos,
# and case 6 above shows the packaged client really runs an LCDd session on the
# OHOS runtime, so this pins the payload ABI as well.
for prog in lcdproc lcdexec lcdvc LCDd; do
    assert_aarch64_elf "$BIN/$prog" "bin/$prog"
done
pass "lcdproc / lcdexec / lcdvc / LCDd are AArch64 (0xB7) ELF binaries"

# Driver plugins are dlopen()ed by LCDd at runtime, so they must carry the same
# ABI as the daemon - a mismatched plugin set would only fail at LCDd startup.
#
# The count is pinned to exactly 10 because the recipe passes an explicit
# --enable-drivers=<list> (upstream's 11 defaults minus `curses`, the only
# default driver with no enable/disable switch).  Without that the count would
# depend on whether the *build host* happened to have ncurses installed, and
# this assertion would be a platform assumption rather than a fact.
n_drv=0
for so in "$DRV"/*.so; do
    [ -e "$so" ] || break
    assert_aarch64_elf "$so" "driver $(basename "$so")"
    n_drv=$((n_drv + 1))
done
[ "$n_drv" -ge 1 ] || fail "no driver plugins found in $DRV"
pass "all $n_drv LCDd driver plugins are AArch64 ELF objects"

# ------------------------------------------- 8. payload completeness
# The suite is only useful if the daemon, its drivers and the shipped
# configuration all landed in the package.
# etc/ is resolved relative to the package root (parent of bin)
CFG_DIR="$BIN/../etc"
for cfg in LCDd.conf lcdproc.conf lcdvc.conf lcdexec.conf; do
    [ -s "$CFG_DIR/$cfg" ] || fail "missing shipped config $CFG_DIR/$cfg"
done
[ "$n_drv" -eq 10 ] \
    || fail "expected 10 driver plugins (--enable-drivers is pinned by the recipe), found $n_drv"
pass "payload complete: LCDd + $n_drv drivers + 4 shipped config files"

echo "All tests passed ($n_pass cases)."
