#!/usr/bin/env bash
# Functional smoke test for the packaged boxshade binary.
# Upstream ships no test suite (no `make check` target), so this test drives the
# packaged CLI and verifies its -help output and a clean exit.
# Running `boxshade -help` needs no input alignment and no runtime data files.
set -euo pipefail

BOXSHADE_BIN="${BOXSHADE_BIN:-boxshade}"

help_output="$("$BOXSHADE_BIN" -help 2>&1 || true)"
case "$help_output" in
  *"Allowed command line parameters are:"*) ;;
  *)
    echo "Unexpected boxshade help output:"
    echo "$help_output"
    exit 1
    ;;
esac

"$BOXSHADE_BIN" -help >/dev/null 2>&1

echo "boxshade smoke test passed"
