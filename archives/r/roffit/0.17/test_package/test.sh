#!/bin/bash
# test_package/test.sh — L0c test source for roffit
# Replays the upstream `make test` golden-file case against the packaged
# roffit, using the perl interpreter resolved via conanrun env PATH.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"

ROFFIT="$(command -v roffit)"
PERL="${PERL_BIN:-perl}"

echo "[test] roffit --version"
"$PERL" "$ROFFIT" --version | grep -q "0.17" || {
    echo "❌ roffit --version did not report 0.17"
    exit 1
}
echo "✅ roffit --version OK"

echo "[test] upstream golden-file case (make test equivalent)"
"$PERL" "$ROFFIT" --bare < "$DIR/testpage.1" > "$DIR/testpage.dump.actual"
if cmp -s "$DIR/testpage.dump.actual" "$DIR/testpage.output"; then
    echo "✅ golden-file compare OK"
else
    echo "❌ golden-file mismatch"
    diff -u "$DIR/testpage.output" "$DIR/testpage.dump.actual" || true
    exit 1
fi
rm -f "$DIR/testpage.dump.actual"
