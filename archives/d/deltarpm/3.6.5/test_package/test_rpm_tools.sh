#!/bin/sh
# test_rpm_tools.sh — smoke case 2/2 for deltarpm test_package.
# Invokes makedeltarpm/applydeltarpm/combinedeltarpm/fragiso with no (or bad)
# args and asserts each binary executes its real main() by matching its
# diagnostic output. Empty output or a bare `exit 1` stub fails the greps.
set -eu

# ---- HMBS readonly /tmp compat: pick a writable tmp dir first ----
_HMBS_TMP=""
for _cand in "${TMPDIR:-}" "${TMP:-}" "${TEMP:-}"; do
    if [ -n "${_cand:-}" ] && [ "$_cand" != "0" ] && [ "$_cand" != "1" ] \
        && [ -d "$_cand" ] && [ -w "$_cand" ]; then
        _HMBS_TMP="$_cand"
        break
    fi
done
if [ -n "${_HMBS_TMP:-}" ]; then
    TMPDIR="$_HMBS_TMP"; TMP="$_HMBS_TMP"; TEMP="$_HMBS_TMP"
else
    TMPDIR="${TMPDIR:-./tmp}"; TMP="$TMPDIR"; TEMP="$TMPDIR"
    mkdir -p "$TMPDIR" 2>/dev/null || true
fi
export TMPDIR TMP TEMP

BINDIR="${1:?usage: test_rpm_tools.sh <bindir>}"

# Binaries must exist and be non-empty (anti-empty-artifact check).
for _t in makedeltarpm applydeltarpm combinedeltarpm fragiso; do
    [ -s "$BINDIR/$_t" ] || { echo "[fail] $_t missing or empty"; exit 1; }
done
echo "[ok] makedeltarpm/applydeltarpm/combinedeltarpm/fragiso present and non-empty"

OUT="$TMPDIR/deltarpm_rpm_tools.log"
: > "$OUT" 2>/dev/null || true

# combinedeltarpm with no args must print usage and exit nonzero.
if "$BINDIR/combinedeltarpm" >"$OUT" 2>&1; then
    echo "[fail] combinedeltarpm unexpectedly exited 0 with no args"
    exit 1
fi
grep -q "usage: combinedeltarpm" "$OUT" || { echo "[fail] combinedeltarpm usage text missing:"; cat "$OUT"; exit 1; }
echo "[ok] combinedeltarpm prints usage on no-arg invocation"

# fragiso with no args must print usage and exit nonzero.
if "$BINDIR/fragiso" >"$OUT" 2>&1; then
    echo "[fail] fragiso unexpectedly exited 0 with no args"
    exit 1
fi
grep -q "usage: fragiso" "$OUT" || { echo "[fail] fragiso usage text missing:"; cat "$OUT"; exit 1; }
echo "[ok] fragiso prints usage on no-arg invocation"

# makedeltarpm / applydeltarpm: require nonzero exit plus non-empty,
# self-identifying diagnostic output (exact usage wording not audited upstream,
# so match the program name instead of a guessed string).
if "$BINDIR/makedeltarpm" >"$OUT" 2>&1; then
    echo "[fail] makedeltarpm unexpectedly exited 0 with no args"
    exit 1
fi
[ -s "$OUT" ] || { echo "[fail] makedeltarpm produced no output"; exit 1; }
grep -qi "makedeltarpm" "$OUT" || { echo "[fail] makedeltarpm output unrecognized:"; cat "$OUT"; exit 1; }
echo "[ok] makedeltarpm executes and emits diagnostics on no-arg invocation"

if "$BINDIR/applydeltarpm" >"$OUT" 2>&1; then
    echo "[fail] applydeltarpm unexpectedly exited 0 with no args"
    exit 1
fi
[ -s "$OUT" ] || { echo "[fail] applydeltarpm produced no output"; exit 1; }
grep -qi "applydeltarpm" "$OUT" || { echo "[fail] applydeltarpm output unrecognized:"; cat "$OUT"; exit 1; }
echo "[ok] applydeltarpm executes and emits diagnostics on no-arg invocation"

echo "[pass] rpm tools usage checks passed"
