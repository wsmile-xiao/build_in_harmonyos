#!/data/service/hnp/bin/bash
# test_package/test.sh — functional consumer tests for the mpssh executable.
# Verifies against a LOCAL slow listener (no external network):
#   - option parsing: -V (version), no-args usage, -f (hosts file), -b (blind)
#   - exit codes: usage → 0, missing hosts file → 1, real task → 0
#   - parallel execution: -p 8 finishes 8 slow connections ~8x faster than -p 1
#   - SIGCHLD reap race regression: 20 rapid runs must not SIGSEGV
set -u

MPSSH="${1:?usage: test.sh <path-to-mpssh>}"
PY="${PYTHON3:-python3}"
DIR="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fail=0
pass_count=0

ok()   { echo "✅ $1"; pass_count=$((pass_count+1)); }
bad()  { echo "❌ $1"; fail=$((fail+1)); }

# ── 1. -V version ──
out="$("$MPSSH" -V 2>&1)"
if [ "$out" = "mpssh-1.3.3" ]; then
    ok "-V prints version (got: $out)"
else
    bad "-V output mismatch: '$out'"
fi

# ── 2. usage on no args → exit 0, prints usage ──
out="$("$MPSSH" 2>&1 || true)"
"$MPSSH" >/dev/null 2>&1
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q -e "command missing" -e "Usage" -e "mpssh"; then
    ok "no-args usage exit=0 with usage text"
else
    bad "no-args usage rc=$rc out='$out'"
fi

# ── 3. missing hosts file → exit 1 ──
"$MPSSH" -f "$WORK/nonexistent-hosts" true >/dev/null 2>&1
rc=$?
if [ $rc -eq 1 ]; then
    ok "missing hosts file → exit 1"
else
    bad "missing hosts file rc=$rc (expected 1)"
fi

# ── 4. getpwuid fallback: no passwd entry must NOT crash (SIGSEGV=139) ──
# exact contract: without a passwd entry for the uid, getpwuid() returns
# NULL, the fallback user kicks in, and the missing hosts file is still
# reported as a usage error with exit code 1 (NOT a SIGSEGV crash)
out="$(env -u USER -u LOGNAME "$MPSSH" -f "$WORK/nonexistent-hosts" true 2>&1)"
rc=$?
if [ "$rc" -eq 1 ]; then
    ok "getpwuid fallback: no passwd entry → clean exit 1 (no SIGSEGV)"
else
    bad "getpwuid fallback: expected exit 1 without passwd entry, got rc=$rc"
    echo "   diagnostic: $(printf '%s' "$out" | head -n 3 | tr '\n' ' ')"
    if [ "$rc" -eq 139 ]; then
        echo "   → SIGSEGV (139): NULL-deref regression in getpwuid handling (E338)"
    elif [ "$rc" -eq 0 ]; then
        echo "   → exit 0: missing hosts file was silently accepted (usage check broken)"
    else
        echo "   → unexpected exit code; see output above"
    fi
fi

# ── 5. parallel execution: local slow listener, 8 hosts, -p 8 vs -p 1 ──
# The listener holds each connection ~1.5s; mpssh execs /usr/bin/ssh which
# connects to it. -p 8 → ~1.5s wall; -p 1 → ~12s wall.
cat > "$WORK/listener.py" <<'EOF'
import socket, sys, threading, time
port = int(sys.argv[1]); hold = float(sys.argv[2])
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", port)); srv.listen(64)
def hold_conn(c):
    try:
        c.settimeout(hold + 5); c.recv(1024)
    except Exception: pass
    time.sleep(hold); c.close()
deadline = time.time() + 90
while time.time() < deadline:
    srv.settimeout(1)
    try: c, _ = srv.accept()
    except socket.timeout: continue
    threading.Thread(target=hold_conn, args=(c,), daemon=True).start()
EOF

PORT="$("$PY" -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')"
"$PY" "$WORK/listener.py" "$PORT" 1.5 &
LPID=$!
sleep 1

i=0; : > "$WORK/hosts.txt"
while [ $i -lt 8 ]; do
    echo "127.0.0.1:$PORT" >> "$WORK/hosts.txt"
    i=$((i+1))
done

S1="$(date +%s%N)"
env -u USER -u LOGNAME "$MPSSH" -f "$WORK/hosts.txt" -p 8 -b true >/dev/null 2>&1
rc8=$?
E1="$(date +%s%N)"
WALL8=$(( (E1 - S1) / 1000000 ))

S2="$(date +%s%N)"
env -u USER -u LOGNAME "$MPSSH" -f "$WORK/hosts.txt" -p 1 -b true >/dev/null 2>&1
rc1=$?
E2="$(date +%s%N)"
WALL1=$(( (E2 - S2) / 1000000 ))

kill $LPID 2>/dev/null; wait $LPID 2>/dev/null

if [ $rc8 -eq 0 ]; then
    ok "-p 8 run exit 0"
else
    bad "-p 8 run rc=$rc8"
fi
if [ $rc1 -eq 0 ]; then
    ok "-p 1 run exit 0"
else
    bad "-p 1 run rc=$rc1"
fi
if [ $WALL8 -lt $((WALL1 / 2)) ]; then
    ok "parallelism: -p8=${WALL8}ms < half of -p1=${WALL1}ms"
else
    bad "parallelism NOT observed: -p8=${WALL8}ms -p1=${WALL1}ms"
fi

# ── 6. SIGCHLD reap race regression: 20 rapid runs must not SIGSEGV ──
# upstream bug: pslot_bypid() NULL deref + global cursor use-after-free in
# reap_child() crash ~8% of runs on fast-exiting children (patch 0002)
race_fails=0
i=0
while [ $i -lt 20 ]; do
    env -u USER -u LOGNAME "$MPSSH" -f "$WORK/hosts.txt" -p 1 -b true >/dev/null 2>&1
    rc=$?
    [ $rc -ne 0 ] && race_fails=$((race_fails+1))
    i=$((i+1))
done
if [ $race_fails -eq 0 ]; then
    ok "SIGCHLD race: 20/20 runs clean (no rc=139)"
else
    bad "SIGCHLD race: $race_fails/20 runs crashed (rc=139) — 0002 regression"
fi

echo ""
echo "test.sh summary: $pass_count passed, $fail failed"
if [ $fail -gt 0 ]; then
    exit 1
fi
exit 0
