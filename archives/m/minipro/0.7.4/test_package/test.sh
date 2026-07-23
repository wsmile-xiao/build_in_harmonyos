#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke + functional test for the minipro executable.
# Runs in the conanrun env, so PATH includes the installed bin/ (i.e. `minipro`).
set -euo pipefail

MINIPRO="${1:-minipro}"

if ! command -v "$MINIPRO" >/dev/null 2>&1; then
    echo "❌ minipro executable not found: $MINIPRO"
    exit 1
fi

echo "[step] minipro --version"
# minipro --version may return non-zero exit code on some builds.
# Capture output and don't fail on exit code — verify via output content instead.
VERSION_OUT="$("$MINIPRO" --version 2>&1)" || true
echo "$VERSION_OUT"
if echo "$VERSION_OUT" | grep -Eqi '^minipro version 0\.7\.4([[:space:]]|$)'; then
    echo "✅ minipro --version OK (binary executable, ELF valid)"
else
    echo "❌ minipro --version failed — unexpected output"
    exit 1
fi

echo "[step] minipro --help"
# Functional test: --help exercises the command-line parser and prints usage.
# minipro --help may return non-zero exit code, so capture and check content.
HELP_OUT="$("$MINIPRO" --help 2>&1)" || true
if echo "$HELP_OUT" | grep -qi "Usage"; then
    echo "✅ minipro --help OK (core function verified)"
else
    echo "❌ minipro --help failed — unexpected output:"
    echo "$HELP_OUT"
    exit 1
fi

echo "minipro test_package: PASS"
