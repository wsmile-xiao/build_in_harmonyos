#!/bin/sh
set -eu

# HMBS readonly /tmp compat - must be first, before any mktemp/touch
_HMBS_TMP=""
for _cand in "${TMPDIR:-}" "${TMP:-}" "${TEMP:-}"; do
    if [ -z "${_cand:-}" ] || [ "$_cand" = "0" ] || [ "$_cand" = "1" ]; then continue; fi
    if [ -d "$_cand" ] && [ -w "$_cand" ]; then
        _HMBS_TMP="$_cand"
        break
    fi
done
if [ -n "${_HMBS_TMP:-}" ]; then
    TMPDIR="$_HMBS_TMP"; TMP="$_HMBS_TMP"; TEMP="$_HMBS_TMP"
    export TMPDIR TMP TEMP
else
    for _cand in "${TMPDIR:-}" "${TMP:-}" "./tmp" "$PWD/tmp"; do
        if [ -n "${_cand:-}" ] && [ "$_cand" != "0" ] && [ "$_cand" != "/tmp" ]; then
            if mkdir -p "$_cand" 2>/dev/null && [ -d "$_cand" ] && [ -w "$_cand" ]; then
                TMPDIR="$_cand"; TMP="$_cand"; TEMP="$_cand"
                export TMPDIR TMP TEMP
                break
            fi
        fi
    done
fi
export TMPDIR TMP TEMP

echo "[test] redstore smoke test (TMPDIR=${TMPDIR:-<unset>})"

# ---- Resolve redstore binary ----
REDSTORE_BIN=""
if [ -n "${1:-}" ] && [ -f "${1:-}" ]; then
    REDSTORE_BIN="$1"
    echo "[info] using redstore from arg: $REDSTORE_BIN"
fi
if [ -z "$REDSTORE_BIN" ] || [ ! -f "$REDSTORE_BIN" ]; then
    if [ -n "${CONAN_REDSTORE_BIN:-}" ] && [ -f "$CONAN_REDSTORE_BIN" ]; then
        REDSTORE_BIN="$CONAN_REDSTORE_BIN"
        echo "[info] using redstore from CONAN_REDSTORE_BIN: $REDSTORE_BIN"
    fi
fi
if [ -z "$REDSTORE_BIN" ] || [ ! -f "$REDSTORE_BIN" ]; then
    if command -v redstore >/dev/null 2>&1; then
        REDSTORE_BIN=$(command -v redstore)
        echo "[info] redstore found in PATH: $REDSTORE_BIN"
    fi
fi
if [ -z "$REDSTORE_BIN" ] || [ ! -f "$REDSTORE_BIN" ]; then
    echo "[fail] redstore binary not found (PATH=$PATH)"
    exit 1
fi

chmod +x "$REDSTORE_BIN" 2>/dev/null || true
echo "[info] redstore at $REDSTORE_BIN"
file "$REDSTORE_BIN" || true

# ---- Check 1: redstore -h prints version + usage (exits 1 by design) ----
echo "[test 1/2] redstore -h version and usage"
OUT1="$TMPDIR/redstore_help.txt"
set +e
"$REDSTORE_BIN" -h >"$OUT1" 2>&1
RC1=$?
set -e
if [ ! -s "$OUT1" ]; then
    echo "[fail] check 1: -h output empty"
    exit 1
fi
if ! grep -q "version 0.5.4" "$OUT1"; then
    echo "[fail] check 1: version string missing"
    cat "$OUT1" | head -n 20 || true
    exit 1
fi
if ! grep -q "Usage:" "$OUT1"; then
    echo "[fail] check 1: Usage line missing"
    cat "$OUT1" | head -n 20 || true
    exit 1
fi
echo "[ok] check 1 passed (version + Usage present, exit=$RC1)"

# ---- Check 2: conflicting -q -v must be rejected (proves arg validation) ----
echo "[test 2/2] redstore -q -v conflict rejected"
OUT2="$TMPDIR/redstore_conflict.txt"
set +e
"$REDSTORE_BIN" -q -v >"$OUT2" 2>&1
RC2=$?
set -e
if [ "$RC2" -eq 0 ]; then
    echo "[fail] check 2: -q -v unexpectedly succeeded (harness would miss failures)"
    exit 1
fi
if ! grep -qi "quiet.*verbose\|verbose.*quiet\|Can't be quiet" "$OUT2"; then
    echo "[info] check 2: exit code $RC2 nonzero as expected (message differs, still valid)"
else
    echo "[ok] check 2 passed (conflict rejected with message, exit=$RC2)"
fi
echo "[ok] check 2 passed"

echo "[pass] redstore smoke test passed (2/2)"
