#!/bin/sh
# test_package/test.sh — functional test for the cdcd executable.
#
# cdcd talks to real optical hardware (/dev/cdrom + CDDB over the network),
# none of which exists in the OHOS build/CI sandbox.  We therefore verify
# the real binary on its hardware-free and fast-failing paths (4 cases):
#   1. binary present and executable
#   2. `cdcd --version` prints "cdcd 0.6.6" and the libcdaudio version line
#   3. `cdcd --help`    prints "Usage: cdcd [options] [commands]"
#   4. a malformed .cdcdrc is rejected (non-zero exit + invalid-file message)
#
# CRITICAL: cdcdrc_read() runs BEFORE getopt in cdcd's main(); a missing
# $HOME/.cdcdrc would start the interactive first-run wizard (stdin
# questions) and hang forever.  Every invocation therefore runs with an
# isolated HOME containing a valid revision-3 rc file (cases 1-3), and
# case 4 swaps in a malformed one.  The real HOME is never touched.
#
# Isolated-home dir is REQUIRED as $2 (conanfile passes a fresh mkdtemp
# under TMPDIR): conan 2 runs test_package IN-PLACE inside the worktree
# ("Test package build folder: .../archives/.../test_package"), so a
# $(pwd)-relative dir would write runtime junk into the commit surface —
# that exact defect was caught by stage_candidate reconciliation once.
set -u

BIN="${1:?usage: test.sh <installed-bin> <isolated-home-dir>}"
HOMEDIR="${2:?usage: test.sh <installed-bin> <isolated-home-dir>}"
PASS=0
FAIL=0

echo "[test] cdcd: locate binary"
if [ -z "${BIN:-}" ]; then
  BIN="$(command -v cdcd || true)"
fi
if [ -z "$BIN" ] || [ ! -f "$BIN" ]; then
  echo "FAIL: cdcd binary not found (arg='${BIN:-}')"
  exit 1
fi
if [ ! -x "$BIN" ]; then
  echo "FAIL: $BIN not executable"
  exit 1
fi
PASS=$((PASS + 1))
echo "[ok] binary at $BIN"

# Isolated HOME with a valid .cdcdrc (revision 3, same bytes cdcdrc_write
# would emit) so cdcdrc_read() takes the file path, not the interactive
# first-run wizard.  $2 comes from conanfile (mkdtemp under TMPDIR, outside
# the worktree); the real HOME is never touched.
rm -rf "$HOMEDIR"
mkdir -p "$HOMEDIR" || { echo "FAIL: cannot create $HOMEDIR"; exit 1; }
{
  echo "# .cdcdrc revision 3"
  echo ""
  echo "verbose=ON"
  echo "device=/dev/nonexistent-cdcd-test-device"
} > "$HOMEDIR/.cdcdrc" || { echo "FAIL: cannot write .cdcdrc"; exit 1; }
export HOME="$HOMEDIR"

echo "[test] cdcd --version prints 0.6.6"
set +e
OUT="$("$BIN" --version < /dev/null 2>&1)"
RC=$?
set -e
echo "  exit=$RC"
if [ "$RC" -ne 0 ]; then
  echo "FAIL: cdcd --version exited $RC"
  FAIL=$((FAIL + 1))
elif ! printf '%s' "$OUT" | grep -q "cdcd 0\.6\.6"; then
  echo "FAIL: version output missing cdcd 0.6.6: $OUT"
  FAIL=$((FAIL + 1))
elif ! printf '%s' "$OUT" | grep -q "Using libcdaudio"; then
  echo "FAIL: output missing 'Using libcdaudio' (runtime linkage line): $OUT"
  FAIL=$((FAIL + 1))
else
  PASS=$((PASS + 1))
  echo "[ok] version + libcdaudio linkage line verified"
fi

echo "[test] cdcd --help prints usage"
set +e
OUT="$("$BIN" --help < /dev/null 2>&1)"
RC=$?
set -e
echo "  exit=$RC"
if [ "$RC" -ne 0 ]; then
  echo "FAIL: cdcd --help exited $RC"
  FAIL=$((FAIL + 1))
elif ! printf '%s' "$OUT" | grep -q "Usage: cdcd \[options\] \[commands\]"; then
  echo "FAIL: help output missing usage line: $OUT"
  FAIL=$((FAIL + 1))
else
  PASS=$((PASS + 1))
  echo "[ok] usage line verified"
fi

echo "[test] malformed .cdcdrc is rejected (config parser negative path)"
{
  echo "# .cdcdrc revision 999 wrong first line"
  echo "verbose=ON"
} > "$HOMEDIR/.cdcdrc" || { echo "FAIL: cannot rewrite .cdcdrc"; exit 1; }
set +e
OUT="$("$BIN" --version < /dev/null 2>&1)"
RC=$?
set -e
echo "  exit=$RC"
if [ "$RC" -eq 0 ]; then
  echo "FAIL: expected non-zero exit for invalid .cdcdrc"
  FAIL=$((FAIL + 1))
elif ! printf '%s' "$OUT" | grep -q "invalid"; then
  echo "FAIL: expected 'invalid' message for malformed rc, got: $OUT"
  FAIL=$((FAIL + 1))
else
  PASS=$((PASS + 1))
  echo "[ok] invalid rc rejected with message"
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$([ "$FAIL" -eq 0 ] && echo true || echo false),\"command\":\"sh test.sh <installed bin/cdcd>\",\"discovered\":4,\"passedCount\":$PASS}"

if [ "$FAIL" -ne 0 ]; then
  echo "[fail] $FAIL case(s) failed, $PASS passed"
  exit 1
fi
echo "[ok] all $PASS test_package cases passed"
