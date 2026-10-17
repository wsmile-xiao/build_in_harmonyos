#!/bin/bash
# test_package/test.sh - sexpect 2.4.0 consumer regression tests.
#
# Runs in the conanrun environment, so the packaged bin/ is on PATH.
# Exercises the installed binary end to end: version, PTY spawn -> send ->
# expect -> wait (child exit status propagation), the platform capability
# path (sockfile under /tmp where OHOS denies pathname AF_UNIX bind and only
# the abstract-namespace fallback can work) and three negative controls
# (timeout classification, rejection without a server).
#
# Note: no `set -e` — the script must execute every assertion and report the
# total; `set -u`/pipefail are kept for typo/unset-variable safety.
set -uo pipefail

pass=0
fail=0
ok()  { pass=$((pass + 1)); echo "  PASS $*"; }
bad() { fail=$((fail + 1)); echo "  FAIL $*"; }

# OHOS mounts /tmp read-only; keep scratch data under $TMPDIR.
scratch="${TMPDIR:-$PWD}/sexpect-tp-$$"
mkdir -p "$scratch"

cleanup() {
    # never leave a sexpect daemon behind on a shared device
    if [ -n "${SEXPECT_SOCKFILE:-}" ]; then
        sexpect kill >/dev/null 2>&1 || true
        sexpect wait >/dev/null 2>&1 || true
    fi
    rm -rf "$scratch"
}
trap cleanup EXIT

echo "[1/4] sexpect version reports the packaged upstream version"
vout=$(sexpect version 2>&1); vrc=$?
if [ "$vrc" -eq 0 ] && [ "$vout" = "sexpect 2.4.0" ]; then
    ok "version -> $vout"
else
    bad "version rc=$vrc out=[$vout]"
fi

echo "[2/4] spawn / send / expect / wait end-to-end (writable scratch sockfile)"
export SEXPECT_SOCKFILE="$scratch/tp.sock"
if sexpect spawn -t 10 -ttl 30 sh -c 'read line; printf "got:%s\n" "$line"; exit 3'; then
    ok "spawn"
else
    bad "spawn rc=$?"
fi
sexpect send -cr 'hello'
out=$(sexpect expect -t 10 -exact 'got:hello'); erc=$?
case "$out" in
    *'got:hello'*) ok "expect -exact got:hello (rc=$erc)" ;;
    *) bad "expect rc=$erc out=[$out]" ;;
esac
sexpect wait; wrc=$?
if [ "$wrc" -eq 3 ]; then
    ok "wait propagates the child exit status (3)"
else
    bad "wait rc=$wrc (want 3)"
fi

echo "[3/4] same flow with SEXPECT_SOCKFILE under /tmp (platform capability path)"
# On OHOS /tmp is read-only and pathname AF_UNIX bind is denied, so this only
# works through the abstract-namespace fallback; on Linux it uses the plain
# pathname socket in /tmp.
export SEXPECT_SOCKFILE="/tmp/sexpect-tp-$$.sock"
if sexpect spawn -t 10 -ttl 30 sh -c 'read line; printf "abs:%s\n" "$line"; exit 5'; then
    ok "spawn with /tmp sockfile"
else
    bad "spawn with /tmp sockfile rc=$?"
fi
sexpect send -cr 'world'
out=$(sexpect expect -t 10 -exact 'abs:world'); erc=$?
case "$out" in
    *'abs:world'*) ok "expect -exact abs:world (rc=$erc)" ;;
    *) bad "expect rc=$erc out=[$out]" ;;
esac
sexpect wait; wrc=$?
if [ "$wrc" -eq 5 ]; then
    ok "wait propagates the child exit status (5)"
else
    bad "wait rc=$wrc (want 5)"
fi

echo "[4/4] negative controls"
export SEXPECT_SOCKFILE="$scratch/tp-tmo.sock"
sexpect spawn -t 2 -ttl 30 sleep 30
sexpect expect -t 1 'never-appears'; trc=$?
if [ "$trc" -ne 0 ]; then
    ok "expect -t 1 returns non-zero ($trc) when the pattern never appears"
else
    bad "expect -t 1 returned 0"
fi
if sexpect chkerr -err "$trc" -is timeout; then
    ok "chkerr classifies $trc as timeout"
else
    bad "chkerr: $trc is not classified as timeout"
fi
sexpect kill >/dev/null 2>&1 || true
sexpect wait >/dev/null 2>&1 || true

export SEXPECT_SOCKFILE="$scratch/no-server.sock"
if sexpect get >/dev/null 2>&1; then
    bad "get succeeded without a server"
else
    ok "get fails without a server (no daemon)"
fi

echo "----------------------------------------"
echo "assertions: $((pass + fail))  passed: $pass  failed: $fail"
[ "$fail" -eq 0 ] || exit 1
echo "ALL TESTS PASSED"
