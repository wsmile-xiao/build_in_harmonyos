#!/bin/sh
# test_package/test_lemonbar.sh — functional test for the packaged lemonbar binary.
# Runs in the conanrun environment (PATH includes the installed bin/ dir).
#
# lemonbar cannot do anything observable before it has an X connection: main()
# calls xconn() *before* getopt(), and xconn() aborts with EXIT_FAILURE when
# xcb_connect() fails.  A CI worker has no X server, so the reachable,
# documented behaviour is the failure path — which is exactly what makes it a
# useful smoke test: main() running at all proves that the whole dynamic link
# chain (libxcb + its extensions + libXau + libXdmcp) resolved through the
# bundled $ORIGIN rpath, because the OHOS loader would otherwise abort with a
# "cannot open shared object" error instead of reaching the xcb call.
#
# NOTE: deliberately not `set -e`: every assertion runs commands that are
# expected to return non-zero (lemonbar exits 1 without a display), and the
# check() helper evaluates them as conditions; errexit would abort the suite
# instead of recording the assertion result.
set -u

BAR="$(command -v lemonbar 2>/dev/null || true)"

WORK="lemonbar-test.$$"
mkdir -p "$WORK"
cd "$WORK" || exit 1

# Guard against a hang: a bar that blocks forever waiting for stdin would
# otherwise stall the whole `conan test` run.
if command -v timeout >/dev/null 2>&1; then
  RUN="timeout 15"
else
  RUN=""
fi

# Run lemonbar with DISPLAY removed from the environment (a CI worker has none).
run_no_display() {
  ( unset DISPLAY; exec $RUN "$BAR" "$@" </dev/null ) >"$1.out" 2>"$1.err"
  return $?
}

run_no_display a
rc_a=$?
run_no_display c -h
rc_c=$?

# A named display that nothing is listening on must degrade the same way.
( DISPLAY=:99 exec $RUN "$BAR" </dev/null ) >b.out 2>b.err
rc_b=$?

n_ok=0
n_fail=0
check() {
  msg="$1"
  shift
  if eval "$@" >/dev/null 2>&1; then
    echo "ok - $msg"
    n_ok=$((n_ok + 1))
  else
    echo "not ok - $msg"
    n_fail=$((n_fail + 1))
  fi
}

echo "1..8"

# 1) the packaged binary is installed on PATH and executable
check "lemonbar is installed on PATH and executable" \
  'test -n "$BAR" && test -x "$BAR"'

# 2) documented startup status without a display: EXIT_FAILURE (1).
#    A loader failure would report 127 (not found) or a library error instead.
check "exits 1 when no X display is available" \
  '[ "$rc_a" -eq 1 ]'

# 3) the failure is reported on stderr with the upstream message
check "reports \"Couldn't connect to X\" on stderr" \
  'grep -q "Couldn'"'"'t connect to X" a.err'

# 4) nothing is written to stdout on the failure path
check "writes nothing to stdout on the failure path" \
  '[ ! -s a.out ]'

# 5) a named but unreachable display degrades identically
check "DISPLAY=:99 (nothing listening) fails the same way" \
  '[ "$rc_b" -eq 1 ] && grep -q "Couldn'"'"'t connect to X" b.err'

# 6) -h never reaches the help/version printf: xconn() runs before getopt(), so
#    the advertised help text is unreachable without an X server (upstream
#    behaviour, asserted here so a future reordering is noticed).
check "-h exits 1 with the X error instead of printing help" \
  '[ "$rc_c" -eq 1 ] && grep -q "Couldn'"'"'t connect to X" c.err && [ ! -s c.out ]'

# 7) the failure is the X connection, not a missing shared library: the whole
#    dependency chain resolved through the bundled $ORIGIN rpath.
check "no dynamic loader errors (bundled libxcb chain resolved)" \
  '! grep -qE "cannot open shared object|library not found|No such file|error while loading" a.err b.err c.err'

# 8) the runtime shared objects really ship next to the binary
check "runtime libraries are bundled next to the binary" \
  'd=$(dirname "$BAR"); test -e "$d/libxcb.so" -o -e "$d/libxcb.so.1"; test -e "$d/libXau.so" -o -e "$d/libXau.so.6"; test -e "$d/libXdmcp.so" -o -e "$d/libXdmcp.so.6"'

cd ..
rm -rf "$WORK"
echo "# lemonbar functional assertions: pass=$n_ok fail=$n_fail"
[ "$n_fail" -eq 0 ]
