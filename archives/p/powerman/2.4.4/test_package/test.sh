#!/data/service/hnp/bin/bash
# test_package/test.sh — R34 smoke suite for powerman 2.4.4 (consumer
# perspective).  Runs in the conanrun env (PATH includes the installed
# bin/ and sbin/; LD_LIBRARY_PATH includes lib/).
#
# Strategy: start a REAL powermand in the foreground-backgrounded
# (powermand has no -f flag: it stays in the foreground by default,
# upstream sharness t0004 runs it exactly like this) listening on an
# uncommon high port, with one coprocess "vpc" device implemented by
# vpc-sim.sh (a bash re-implementation of the upstream t/simulators/vpcd
# protocol subset).  Then drive it through the installed powerman
# client: query / on / off / list.  A trap guarantees the daemon and
# its coprocess are reaped even on failure (no sandbox pollution).
#
# E002: all temp files live under $PWD (OHOS /tmp is read-only).
set -u

PASS=0; FAIL=0
check() { # name expected actual
  if [ "$2" = "$3" ]; then
    echo "PASS: $1"
    PASS=$((PASS+1))
  else
    echo "FAIL: $1 (expected [$2], got [$3])"
    FAIL=$((FAIL+1))
  fi
}

SRCDIR="$(cd "$(dirname "$0")" && pwd)"
BASH_SELF="$(command -v bash || echo /data/service/hnp/bin/bash)"
WORK="$PWD/.smoke-work"
# Uncommon high port: powerman's default is 10101 and the upstream
# sharness suite uses 11xxx; stay clear of both.
PORT=47913
ADDR="127.0.0.1:$PORT"

DAEMON_PID=""
cleanup() {
  if [ -n "$DAEMON_PID" ] && kill -0 "$DAEMON_PID" 2>/dev/null; then
    kill "$DAEMON_PID" 2>/dev/null
    wait "$DAEMON_PID" 2>/dev/null
  fi
}
trap cleanup EXIT INT TERM

rm -rf "$WORK"; mkdir -p "$WORK"

# --- T1/T2: version assertions (client + daemon) ------------------------
V=$(powerman --version 2>&1)
check "T1 powerman --version" "2.4.4" "$V"
VD=$(powermand --version 2>&1)
check "T2 powermand --version" "2.4.4" "$VD"

# --- T3: daemon starts and answers (retry-connect probe) ----------------
cat > "$WORK/powerman.conf" <<EOF
listen "$ADDR"
include "$SRCDIR/vpc.dev"
device "test0" "vpc" "$BASH_SELF $SRCDIR/vpc-sim.sh |&"
node "t[0-15]" "test0"
EOF
if [ -f "$WORK/powerman.conf" ]; then
  echo "PASS: T3 powerman.conf generated"; PASS=$((PASS+1))
else
  echo "FAIL: T3 powerman.conf generated"; FAIL=$((FAIL+1))
fi

powermand -c "$WORK/powerman.conf" >"$WORK/powermand.log" 2>&1 &
DAEMON_PID=$!
powerman --retry-connect=100 --server-host="$ADDR" -d >"$WORK/probe.out" 2>&1
check "T4 daemon alive on probe (retry-connect)" "0" "$?"

# --- T5: initial query: all 16 plugs off ---------------------------------
Q=$(powerman --server-host="$ADDR" -q 2>&1)
check "T5 initial -q all off" "on:      
off:     t[0-15]
unknown: " "$Q"

# --- T6: node listing -----------------------------------------------------
L=$(powerman --server-host="$ADDR" -l 2>&1)
check "T6 -l lists the 16 nodes" "t[0-15]" "$L"

# --- T7: power on t[0-3] --------------------------------------------------
O=$(powerman --server-host="$ADDR" -1 t[0-3] 2>&1); RC=$?
check "T7 -1 t[0-3] exit code" "0" "$RC"
check "T7b -1 t[0-3] output" "Command completed successfully" "$O"

# --- T8: query shows t[0-3] on ---------------------------------------------
Q=$(powerman --server-host="$ADDR" -q 2>&1)
check "T8 -q after -1 t[0-3]" "on:      t[0-3]
off:     t[4-15]
unknown: " "$Q"

# --- T9: power on a second disjoint plug (t15) ----------------------------
O=$(powerman --server-host="$ADDR" -1 t15 2>&1); RC=$?
check "T9 -1 t15 exit code" "0" "$RC"

# --- T10: query shows union (hostlist compression) -------------------------
Q=$(powerman --server-host="$ADDR" -q 2>&1)
check "T10 -q union t[0-3,15]" "on:      t[0-3,15]
off:     t[4-14]
unknown: " "$Q"

# --- T11: power off t[0-3] --------------------------------------------------
O=$(powerman --server-host="$ADDR" -0 t[0-3] 2>&1); RC=$?
check "T11 -0 t[0-3] exit code" "0" "$RC"
check "T11b -0 t[0-3] output" "Command completed successfully" "$O"

# --- T12: query shows only t15 on -------------------------------------------
Q=$(powerman --server-host="$ADDR" -q 2>&1)
check "T12 -q after -0 t[0-3]" "on:      t15
off:     t[0-14]
unknown: " "$Q"

# --- T13: graceful daemon shutdown + no leaked processes --------------------
kill "$DAEMON_PID" 2>/dev/null
wait "$DAEMON_PID" 2>/dev/null
check "T13 daemon exits cleanly on SIGTERM" "0" "$?"
DAEMON_PID=""
sleep 1
LEFT=$(ps -ef | grep -E 'vpc-sim\.sh|powermand -c' | grep -v grep | wc -l)
check "T14 no leaked daemon/coprocess processes" "0" "$LEFT"

rm -rf "$WORK"

echo ""
echo "=== powerman test.sh summary: PASS=$PASS FAIL=$FAIL ==="
[ "$FAIL" -eq 0 ]
