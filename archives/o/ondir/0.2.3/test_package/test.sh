#!/data/service/hnp/bin/bash
# test_package/test.sh — functional verification of the ondir CLI tool.
#
# R34: genuinely executes the built ondir binary and asserts observable
# behaviour (it is not a print-only stub). CI's destructive L1e check re-runs
# this script with the package's bin/ moved away and expects a failure,
# proving the test really depends on the ondir artifact.
#
# Usage: bash test.sh <package_folder>
set -euo pipefail

PKG_ROOT="${1:?usage: test.sh <package_folder>}"
BIN="$PKG_ROOT/bin/ondir"

# ── 1. binary is installed and executable ────────────────────────────
echo "[test] 1. binary installed and executable"
[ -x "$BIN" ] || { echo "FAIL: $BIN is missing or not executable"; exit 1; }

# ── 2. -V reports the 0.2.3 release ─────────────────────────────────
echo "[test] 2. ondir -V reports version 0.2.3"
VOUT="$("$BIN" -V)"
echo "    -> $VOUT"
case "$VOUT" in
    *"OnDir version 0.2.3"*) : ;;
    *) echo "FAIL: unexpected -V output: $VOUT"; exit 1 ;;
esac

# ── 3. no-argument invocation: non-zero exit + documented usage ─────
echo "[test] 3. no-argument invocation exits non-zero with usage text"
set +e
UOUT="$("$BIN" 2>&1)"
URC=$?
set -e
echo "    -> exit=$URC"
[ "$URC" -ne 0 ] || { echo "FAIL: no-arg invocation should exit non-zero"; exit 1; }
case "$UOUT" in
    *"Not enough arguments"*) : ;;
    *) echo "FAIL: 'Not enough arguments' not printed"; exit 1 ;;
esac
case "$UOUT" in
    *"usage: ondir [-V] <old-directory> [<new-directory>]"*) : ;;
    *) echo "FAIL: documented usage line not printed"; exit 1 ;;
esac

# ── 4. unknown option is rejected ───────────────────────────────────
echo "[test] 4. unknown option is rejected with a non-zero exit"
set +e
"$BIN" --bogus >/dev/null 2>&1
ORC=$?
set -e
[ "$ORC" -ne 0 ] || { echo "FAIL: unknown option should exit non-zero"; exit 1; }

# ── 5. functional: enter/leave hooks fire on a directory change ─────
echo "[test] 5. functional enter/leave hook emission"
BASE="${TMPDIR:-${HOME:?HOME is not set}/tmp}/ondir-test-$$"
rm -rf "$BASE"
mkdir -p "$BASE/home"
trap 'rm -rf "$BASE"' EXIT
cat > "$BASE/home/.ondirrc" <<'RC'
enter /ondir_test/child
  echo ENTER_CHILD
leave /ondir_test/child
  echo LEAVE_CHILD
RC
ENTER_OUT="$(HOME="$BASE/home" "$BIN" /ondir_test /ondir_test/child)"
echo "    -> enter: $ENTER_OUT"
[ "$ENTER_OUT" = "echo ENTER_CHILD" ] || { echo "FAIL: enter hook not emitted"; exit 1; }
LEAVE_OUT="$(HOME="$BASE/home" "$BIN" /ondir_test/child /ondir_test)"
echo "    -> leave: $LEAVE_OUT"
printf '%s\n' "$LEAVE_OUT" | grep -q "echo LEAVE_CHILD" || { echo "FAIL: leave hook not emitted"; exit 1; }

# ── 6. installed man page / example / hooks / docs are present ──────
echo "[test] 6. installed man / example / hook / doc files"
for f in \
    share/man/man1/ondir.1 \
    share/ondir/scripts.sh \
    share/ondir/scripts.tcsh \
    share/ondir/scripts.zsh \
    share/ondir/ondirrc.eg \
    share/doc/ondir/README.rst \
    share/doc/ondir/COPYING \
    share/doc/ondir/ChangeLog \
    share/doc/ondir/AUTHORS \
    share/doc/ondir/INSTALL ; do
    [ -s "$PKG_ROOT/$f" ] || { echo "FAIL: missing installed file: $f"; exit 1; }
    echo "    -> ok: $f"
done

echo "ALL TESTS PASSED"
