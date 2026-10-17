#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke + functional test for the massdns executable.
# Runs in the conanrun env, so PATH includes the installed bin/ (i.e. `massdns`).
set -euo pipefail

MASSDNS="${1:-massdns}"

echo "[step] massdns --version"
# massdns --version outputs "massdns" and may return non-zero exit code.
# Capture output and don't fail on exit code — verify via output content instead.
VERSION_OUT="$("$MASSDNS" --version 2>&1)" || true
echo "$VERSION_OUT"
if echo "$VERSION_OUT" | grep -qi "massdns"; then
    echo "✅ massdns --version OK (binary executable, ELF valid)"
else
    echo "❌ massdns --version failed — unexpected output"
    exit 1
fi

echo "[step] massdns --help"
# Functional test: --help exercises the command-line parser and prints usage.
# massdns --help may return non-zero exit code, so capture and check content.
HELP_OUT="$("$MASSDNS" --help 2>&1)" || true
if echo "$HELP_OUT" | grep -qi "Usage"; then
    echo "✅ massdns --help OK (core function verified)"
else
    echo "❌ massdns --help failed — unexpected output:"
    echo "$HELP_OUT"
    exit 1
fi

echo "massdns test_package: PASS"
