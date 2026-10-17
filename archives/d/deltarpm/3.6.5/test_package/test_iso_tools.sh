#!/bin/sh
# test_iso_tools.sh — smoke case 1/2 for deltarpm test_package.
# Invokes makedeltaiso/applydeltaiso with no args (each prints its usage text
# and exits nonzero) and asserts on the real diagnostic output.
# An `exit 1` stub binary would print nothing and fail the grep assertions,
# so this harness provably catches non-functional binaries.
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

BINDIR="${1:?usage: test_iso_tools.sh <bindir>}"

# Binaries must exist and be non-empty (anti-empty-artifact check).
[ -s "$BINDIR/makedeltaiso" ] || { echo "[fail] makedeltaiso missing or empty"; exit 1; }
[ -s "$BINDIR/applydeltaiso" ] || { echo "[fail] applydeltaiso missing or empty"; exit 1; }
echo "[ok] makedeltaiso/applydeltaiso present and non-empty"

OUT="$TMPDIR/deltarpm_iso_tools.log"
: > "$OUT" 2>/dev/null || true

# makedeltaiso with no args must print usage and exit nonzero.
if "$BINDIR/makedeltaiso" >"$OUT" 2>&1; then
    echo "[fail] makedeltaiso unexpectedly exited 0 with no args"
    exit 1
fi
grep -q "usage: makedeltaiso" "$OUT" || { echo "[fail] makedeltaiso usage text missing:"; cat "$OUT"; exit 1; }
echo "[ok] makedeltaiso prints usage on no-arg invocation"

# applydeltaiso with no args must print usage and exit nonzero.
if "$BINDIR/applydeltaiso" >"$OUT" 2>&1; then
    echo "[fail] applydeltaiso unexpectedly exited 0 with no args"
    exit 1
fi
grep -q "usage: applydeltaiso" "$OUT" || { echo "[fail] applydeltaiso usage text missing:"; cat "$OUT"; exit 1; }
echo "[ok] applydeltaiso prints usage on no-arg invocation"

[ -s "$OUT" ] || { echo "[fail] captured log unexpectedly empty"; exit 1; }
echo "[pass] iso tools usage checks passed"
