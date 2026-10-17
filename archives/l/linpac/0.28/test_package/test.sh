#!/data/service/hnp/bin/bash
# test_package/test.sh — end-to-end test for the LinPac terminal.
#
# Runs inside the conanrun env, so PATH already contains the package bin/ and
# libexec/linpac/ directories and LD_LIBRARY_PATH the package lib/.
#
# Assertions:
#   1. the real terminal binary (libexec/linpac/linpac) is installed
#   2. it starts and reports its version
#   3. it creates its per-user lock file in a writable runtime directory
#      (OHOS has no /var/lock — this is the OHOS-specific adaptation)
#   4. the explicit LINPAC_LOCKDIR override is honoured
#   5. the bundled LinPac application-protocol helpers are installed
set -euo pipefail

fail() { echo "❌ $*"; exit 1; }

# ── 1. locate the terminal binary ──────────────────────────────────────────
LINPAC_REAL=""
for candidate in $(type -ap linpac 2>/dev/null); do
    case "$candidate" in
        */libexec/linpac/linpac) LINPAC_REAL="$candidate" ;;
    esac
done
[ -n "$LINPAC_REAL" ] || fail "libexec/linpac/linpac is not on PATH (type -ap linpac: $(type -ap linpac 2>/dev/null | tr '\n' ' '))"
[ -x "$LINPAC_REAL" ] || fail "$LINPAC_REAL is not executable"
echo "✅ terminal binary installed: $LINPAC_REAL"

# ── scratch space (never use /tmp on OHOS: read-only) ──────────────────────
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
WORK="$SCRATCH/linpac-test-$$"
rm -rf "$WORK"
mkdir -p "$WORK/home" "$WORK/tmp"
trap 'rm -rf "$WORK"' EXIT

# ── 2. start the terminal and check the version banner ─────────────────────
# There is no AX.25 kernel stack and no controlling terminal here: the program
# prints its banner, takes the lock and then stops at the curses init.
HOME="$WORK/home" TMPDIR="$WORK/tmp" TERM=xterm \
    timeout 60 "$LINPAC_REAL" </dev/null >"$WORK/run.log" 2>&1 || true

grep -q "LinPac version 0.28" "$WORK/run.log" \
    || fail "version banner missing, log: $(head -5 "$WORK/run.log" | tr '\n' ' ')"
echo "✅ startup banner: $(grep -m1 'LinPac version' "$WORK/run.log")"

# ── 3. lock file must land in the writable runtime dir, not /var/lock ──────
LOCK=$(ls "$WORK"/tmp/LinPac.* 2>/dev/null | head -1 || true)
[ -n "$LOCK" ] || fail "no lock file under \$TMPDIR ($WORK/tmp): $(head -5 "$WORK/run.log" | tr '\n' ' ')"
case "$(basename "$LOCK")" in
    LinPac.*) : ;;
    *) fail "lock file name truncated: $(basename "$LOCK")" ;;
esac
if [ -e /var/lock ]; then
    fail "/var/lock exists — the OHOS fallback was not what was exercised"
fi
echo "✅ lock file created in writable runtime dir: $(basename "$LOCK") (/var/lock absent, as on OHOS)"

# ── 4. explicit override wins ─────────────────────────────────────────────
mkdir -p "$WORK/lockdir"
HOME="$WORK/home" LINPAC_LOCKDIR="$WORK/lockdir" TERM=xterm \
    timeout 60 "$LINPAC_REAL" </dev/null >"$WORK/run2.log" 2>&1 || true
[ -n "$(ls "$WORK"/lockdir/LinPac.* 2>/dev/null || true)" ] \
    || fail "LINPAC_LOCKDIR override ignored: $(head -5 "$WORK/run2.log" | tr '\n' ' ')"
echo "✅ LINPAC_LOCKDIR override honoured"

# ── 5. the LinPac application-protocol helpers are installed ──────────────
BINDIR="$(dirname "$LINPAC_REAL")"
for helper in mail testapp mheard telnet; do
    [ -x "$BINDIR/$helper" ] || fail "helper program $helper missing in $BINDIR"
done
echo "✅ helper programs installed: mail testapp mheard telnet"

echo "[test] all linpac assertions passed"
