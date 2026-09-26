#!/bin/sh
# Real consumer test for the packaged ifmetric binary (HarmonyOS PC).
#
# ifmetric has no read-only mode: `ifmetric <iface> [metric]` always issues
# RTM_DELROUTE + RTM_NEWROUTE for every main-table IPv4 route bound to <iface>.
# So every assertion here is deliberately built so that zero routes can match:
#   * a nonexistent interface name aborts in getifn() before any route work;
#   * an interface that has no entry in /proc/net/route (= the main table, which
#     is exactly what enumerate() filters on RT_TABLE_MAIN) exercises the whole
#     read path but yields n_routes == 0, so no write is ever sent.
# The table is additionally snapshotted before/after and compared.
#
# Deliberately no `set -euo pipefail`: this harness collects verdicts from the
# exit status of calls that are *expected* to fail (assertion 4 needs rc=1) and
# keeps going to report every assertion; `set -e` would abort on the first
# intentional failure and turn a real check into a false negative.

EXE="$1"
if [ -z "$EXE" ]; then
    echo "usage: smoke.sh <path-to-ifmetric>" >&2
    exit 2
fi

TMPD="${TMPDIR:-$HOME/tmp}/ifmetric-smoke"
mkdir -p "$TMPD" 2>/dev/null || { echo "cannot create $TMPD" >&2; exit 2; }
OUT="$TMPD/out.txt"
ERR="$TMPD/err.txt"

TOTAL=0
PASS=0
SKIP=0

ok() {
    TOTAL="$((TOTAL + 1))"
    PASS="$((PASS + 1))"
    echo "ok       - $1"
}
bad() {
    TOTAL="$((TOTAL + 1))"
    echo "NOT OK   - $1"
}
skip() {
    TOTAL="$((TOTAL + 1))"
    SKIP="$((SKIP + 1))"
    echo "skipped  - $1"
}

# ---------------------------------------------------------------- binary sanity
if [ -x "$EXE" ]; then
    ok "packaged binary exists and is executable: $EXE"
else
    bad "packaged binary missing or not executable: $EXE"
    echo "CONSUMER_RESULT 0/1"
    exit 1
fi

# ------------------------------------------------- 1) usage on bare invocation
: >"$OUT"; : >"$ERR"
"$EXE" >"$OUT" 2>"$ERR"
rc=$?
if [ "$rc" = "0" ] && grep -q "Usage:" "$OUT" && grep -q "metric" "$OUT"; then
    ok "bare invocation prints usage and exits 0 (argc<=1 branch)"
else
    bad "bare invocation: rc=$rc usage=$(grep -c 'Usage:' "$OUT")"
    sed -e 's/^/    stdout| /' "$OUT" -e 's/^/    stderr| /' "$ERR"
fi

# ------------------------------------------------------- 2) --help is not an arg
: >"$OUT"; : >"$ERR"
"$EXE" --help >"$OUT" 2>"$ERR"
rc=$?
if [ "$rc" = "0" ] && grep -q "Usage:" "$OUT"; then
    ok "--help prints usage and exits 0 without touching netlink"
else
    bad "--help: rc=$rc"
    sed -e 's/^/    stdout| /' "$OUT" -e 's/^/    stderr| /' "$ERR"
fi

# ------------- 3) nonexistent iface: proves the rtnetlink round trip completed
# getifn() sends RTM_GETLINK and walks the reply; only a working socket()+bind()
# +send()+recv() chain can produce "not existent" (as opposed to a syscall error).
GHOST=hw2nosuchif0
: >"$OUT"; : >"$ERR"
"$EXE" "$GHOST" 5 >"$OUT" 2>"$ERR"
rc=$?
if [ "$rc" = "1" ] && grep -q "not existent" "$ERR" \
   && ! grep -q "socket(PF_NETLINK)" "$ERR" \
   && ! grep -q "^bind():" "$ERR" \
   && ! grep -q "NETLINK: send()" "$ERR"; then
    ok "netlink read path works end to end (RTM_GETLINK answered; absent iface -> rc=1)"
else
    bad "nonexistent iface: rc=$rc"
    sed -e 's/^/    stderr| /' "$ERR"
    echo "    (a socket()/bind()/send() error here means the netlink API is unusable)"
fi

# --------------- 4/5) route-less real iface: full success path, zero mutation
IFACE=""
awk 'NR > 2 { sub(/:/, "", $1); print $1 }' /proc/net/dev >"$TMPD/dev.txt" 2>/dev/null
awk 'NR > 1 { print $1 }' /proc/net/route >"$TMPD/rt.txt" 2>/dev/null
if [ -s "$TMPD/dev.txt" ]; then
    while read -r d; do
        [ -z "$d" ] && continue
        if ! grep -qx "$d" "$TMPD/rt.txt"; then
            IFACE="$d"
            break
        fi
    done <"$TMPD/dev.txt"
fi

if [ -z "$IFACE" ]; then
    skip "no route-less interface available for the zero-mutation assertion"
    skip "routing table unchanged after a successful invocation (depends on above)"
else
    cp /proc/net/route "$TMPD/route.before" 2>/dev/null
    : >"$OUT"; : >"$ERR"
    "$EXE" "$IFACE" 7 >"$OUT" 2>"$ERR"
    rc=$?
    if [ "$rc" = "0" ] && ! grep -q "NETLINK: Error" "$ERR" \
       && ! grep -q "not existent" "$ERR"; then
        ok "getifn() resolved real iface '$IFACE' and RTM_GETROUTE enumeration completed (rc=0)"
    else
        bad "real iface '$IFACE': rc=$rc"
        sed -e 's/^/    stderr| /' "$ERR"
    fi

    cp /proc/net/route "$TMPD/route.after" 2>/dev/null
    if [ -f "$TMPD/route.before" ] && diff "$TMPD/route.before" "$TMPD/route.after" >/dev/null 2>&1; then
        ok "main routing table byte-identical before/after (no route was mutated)"
    else
        bad "routing table changed or could not be sampled"
    fi
fi

echo "CONSUMER_RESULT $PASS/$TOTAL (skipped=$SKIP)"
if [ "$PASS" = "$TOTAL" ]; then
    exit 0
fi
if [ "$SKIP" != "0" ] && [ "$((PASS + SKIP))" = "$TOTAL" ]; then
    # Environment-dependent assertion unavailable, but everything runnable passed.
    exit 0
fi
exit 1
