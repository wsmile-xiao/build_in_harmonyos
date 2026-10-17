#!/bin/bash
# L1 test source file — jupyter-events 0.12.0 (R34: substantial CLI test)
# Runs the actual `jupyter-events` binary and exercises schema validation.
# The authoritative tests run via test_package/conanfile.py test() method;
# this script is the equivalent shell view for CI source-file checks (L0c).
#
# Use bash shebang (not sh): historically needed for pipefail; CI may still
# invoke via `sh test.sh`, so avoid bash-only options like pipefail.

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GOOD="$SCRIPT_DIR/schemas/good.json"
BAD="$SCRIPT_DIR/schemas/bad.json"

# Resolve the binary: prefer PATH, fall back to the common staging prefix.
BIN="${JUPYTER_EVENTS_BIN:-$(command -v jupyter-events || echo "$HOME/usr/local/bin/jupyter-events")}"

echo "==> jupyter-events --version"
"$BIN" --version

echo "==> jupyter-events --help"
# Avoid pipefail (CI may run this with `sh`); fail if --help fails or usage missing.
HELP_OUT="$SCRIPT_DIR/.jupyter-events-help.out"
"$BIN" --help >"$HELP_OUT"
grep -q "Usage: jupyter-events" "$HELP_OUT"
rm -f "$HELP_OUT"

echo "==> jupyter-events validate (good schema, expect exit 0)"
"$BIN" validate "$GOOD"

echo "==> jupyter-events validate (bad schema, expect exit 1)"
if "$BIN" validate "$BAD"; then
    echo "ERROR: bad schema unexpectedly validated OK" >&2
    exit 1
fi

echo "ALL CLI TESTS PASSED"
