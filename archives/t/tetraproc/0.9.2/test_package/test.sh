#!/bin/bash
# Consumer smoke test for tetrafile (runs on the OHOS device / Linux host).
# `tetrafile --help` intentionally exits 1 after printing the usage banner.
set -u

: "${TETRAFILE:?TETRAFILE must point to the installed tetrafile binary}"
if [ -n "${RUNTIME_LIBS:-}" ]; then
    export LD_LIBRARY_PATH="$RUNTIME_LIBS${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

out="$("$TETRAFILE" --help 2>&1)"
rc=$?
echo "$out"

case "$out" in
    *"Usage: tetrafile"*) ;;
    *) echo "FAIL: no tetrafile usage banner" ; exit 2 ;;
esac

if [ "$rc" -ne 1 ]; then
    echo "FAIL: unexpected exit code: $rc (expected 1)"
    exit 2
fi

echo "tetrafile --help OK (exit 1 with usage banner, as upstream)"
exit 0
