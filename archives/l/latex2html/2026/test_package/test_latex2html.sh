#!/usr/bin/env bash
set -euo pipefail
L2H_BIN="${1:-latex2html}"
TMPDIR_ARG="${TMPDIR:-}"
if [ -z "$TMPDIR_ARG" ] || [ ! -d "$TMPDIR_ARG" ] || [ ! -w "$TMPDIR_ARG" ]; then
    echo "[test] TMPDIR unusable: '${TMPDIR_ARG:-<empty>}' (empty/missing/non-writable)"
    exit 2
fi
echo "[test] TMPDIR=${TMPDIR_ARG}"
echo "[test] latex2html -tmp \"${TMPDIR_ARG}\" --version"
if "$L2H_BIN" -tmp "$TMPDIR_ARG" --version; then
    echo " latex2html --version OK"
else
    rc=$?
    echo " latex2html --version failed (exit ${rc})"
    exit "${rc}"
fi
echo "[test] latex2html smoke test: PASS"
