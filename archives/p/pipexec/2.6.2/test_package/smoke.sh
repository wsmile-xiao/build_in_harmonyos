#!/bin/sh
# test_package/smoke.sh — pipexec 2.6.2 consumer smoke test (test_package L1).
#
# Drives the *packaged* pipexec binary (never a build-tree copy) through 11
# checks that exercise the features pipexec exists for: constructing process
# trees, wiring fds, runtime restart, child exit-code propagation and argument
# handling.  All child processes are supplied by the pipehelper built in
# conanfile.py::build() and passed in by absolute path, because pipexec execs
# children by absolute path via execv().
#
# Usage: sh smoke.sh <pipexec> <pipehelper> <workdir>
# Any check that does not hold exits non-zero with a FAIL line.
set -eu

PM=${1:?usage: smoke.sh <pipexec> <pipehelper> <workdir>}
HELPER=${2:?usage: smoke.sh <pipexec> <pipehelper> <workdir>}
WORK=${3:?usage: smoke.sh <pipexec> <pipehelper> <workdir>}

[ -x "$PM" ] || { echo "FAIL: pipexec not executable: $PM" >&2; exit 1; }
[ -x "$HELPER" ] || { echo "FAIL: pipehelper not executable: $HELPER" >&2; exit 1; }
[ -d "$WORK" ] || mkdir -p "$WORK"

PASS=0
TOTAL=11
fail() { echo "FAIL: $1" >&2; exit 1; }
ok()   { PASS=$((PASS + 1)); echo "  [ok] $1"; }

# ── T1 -h prints the version banner ──────────────────────────────────────
out=$("$PM" -h 2>&1 || true)
case "$out" in
  *"pipexec version 2.6.2"*) ok "T1 -h banner (pipexec version 2.6.2)" ;;
  *) fail "T1 -h banner missing 'pipexec version 2.6.2' (got: $out)" ;;
esac

# ── T2 no arguments -> usage + exit 1 ────────────────────────────────────
set +e
"$PM" >/dev/null 2>&1
rc=$?
set -e
[ "$rc" -eq 1 ] || fail "T2 no-args exit code (want 1, got $rc)"
ok "T2 no arguments -> exit 1"

# ── T3 all children succeed -> pipexec exits 0 ───────────────────────────
"$PM" -- [ A "$HELPER" exit 0 ] >/dev/null 2>&1 \
  || fail "T3 single successful child should exit 0"
ok "T3 all children succeed -> exit 0"

# ── T4 one child fails -> pipexec exits non-zero ─────────────────────────
set +e
"$PM" -- [ A "$HELPER" exit 0 ] [ B "$HELPER" exit 3 ] >/dev/null 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ] || fail "T4 child failure must make pipexec exit non-zero"
ok "T4 failing child -> non-zero exit ($rc)"

# ── T5 one-to-one pipe: ECHO:1 -> CAT:0, CAT:1 -> stdout ─────────────────
got=$("$PM" -- \
  [ ECHO "$HELPER" echo Hello World ] \
  [ CAT "$HELPER" pass ] \
  '{ECHO:1>CAT:0}' 2>/dev/null)
[ "$got" = "Hello World" ] || fail "T5 echo|pass mismatch (got '$got')"
ok "T5 fd wiring: echo | pass -> 'Hello World'"

# ── T6 multi-stage chain: A -> B -> C over two pipes, data intact ────────
# (pipexec 2.6.2 forbids duplicate pipe ends — one source and one target fd
#  may each appear only once — so fan-in/fan-out is not expressible; a
#  multi-stage chain is.)
"$PM" -- \
  [ A "$HELPER" produce 4096 ] \
  [ B "$HELPER" pass ] \
  [ C "$HELPER" consume "$WORK/t6.out" 4096 ] \
  '{A:1>B:0}' '{B:1>C:0}' >/dev/null 2>&1 \
  || fail "T6 3-stage chain run failed"
"$HELPER" produce 4096 > "$WORK/t6.in"
cmp "$WORK/t6.in" "$WORK/t6.out" \
  || fail "T6 3-stage chain corrupted data"
ok "T6 3-stage chain A->B->C preserves 4096 bytes over two pipes"

# ── T7 data integrity: 65536 deterministic bytes survive produce|pass ────
"$HELPER" produce 65536 > "$WORK/t7.in"
"$PM" -- \
  [ P "$HELPER" produce 65536 ] \
  [ C "$HELPER" consume "$WORK/t7.out" 65536 ] \
  '{P:1>C:0}' >/dev/null 2>&1 \
  || fail "T7 produce|consume run failed"
cmp "$WORK/t7.in" "$WORK/t7.out" \
  || fail "T7 payload corrupted (in/out differ)"
ok "T7 65536-byte payload integrity through the pipe"

# ── T8 -j json logging emits a JSON object ───────────────────────────────
"$PM" -j 3 -- [ A "$HELPER" exit 0 ] 3> "$WORK/t8.json" >/dev/null 2>&1 \
  || fail "T8 -j run failed"
grep -q '^{' "$WORK/t8.json" || fail "T8 -j produced no JSON (got: $(cat "$WORK/t8.json"))"
grep -q '}' "$WORK/t8.json" || fail "T8 -j JSON not closed"
ok "T8 -j json logging emits a JSON object"

# ── T9 -p writes pipexec's own pid (observed while pipexec is alive) ─────
# pipexec removes the pidfile on normal exit, so it has to be read while a
# long-running child keeps pipexec in its wait loop.  The recorded pid must be
# pipexec's own pid.
"$PM" -p "$WORK/t9.pid" -- [ A "$HELPER" sleep 3 ] >/dev/null 2>&1 &
pm_pid=$!
found=0
for _ in 1 2 3 4 5; do
  if [ -s "$WORK/t9.pid" ]; then found=1; break; fi
  sleep 1
done
if [ "$found" -ne 1 ]; then
  kill "$pm_pid" 2>/dev/null || true
  fail "T9 -p did not write the pidfile while running"
fi
recorded=$(tr -d '\n\t ' < "$WORK/t9.pid")
wait "$pm_pid" 2>/dev/null || true
[ "$recorded" = "$pm_pid" ] \
  || fail "T9 pidfile content is '$recorded', expected pipexec pid $pm_pid"
ok "T9 -p writes pipexec's own pid ($recorded)"

# ── T10 -s restart: an abnormally-terminating child is restarted ─────────
# pipexec only restarts after *abnormal* termination (source: set_restart(1)
# on !WIFEXITED/WIFSIGNALED).  abort-once kills itself with SIGABRT on the
# first run and exits 0 afterwards, so exactly two runs must be observed.
set +e
"$PM" -s 1 -- [ A "$HELPER" abort-once "$WORK/t10.marker" ] \
  > "$WORK/t10.log" 2>&1
set -e
[ -f "$WORK/t10.marker" ] || fail "T10 helper never ran"
runs=$(grep -c "aborting to trigger pipexec restart" "$WORK/t10.log" || true)
second=$(grep -c "marker present, exiting 0" "$WORK/t10.log" || true)
[ "$runs" -eq 1 ] || fail "T10 expected 1 aborting run (got $runs)"
[ "$second" -eq 1 ] || fail "T10 expected 1 restarted run (got $second)"
ok "T10 -s restart: child re-run after abnormal termination (2 runs)"

# ── T11 argument forwarding: args reach the child verbatim ───────────────
got=$("$PM" -- \
  [ A "$HELPER" echo alpha beta gamma ] \
  [ B "$HELPER" pass ] \
  '{A:1>B:0}' 2>/dev/null)
[ "$got" = "alpha beta gamma" ] || fail "T11 args not forwarded (got '$got')"
ok "T11 child arguments forwarded verbatim"

echo "pipexec-smoke-ok $PASS/$TOTAL"
