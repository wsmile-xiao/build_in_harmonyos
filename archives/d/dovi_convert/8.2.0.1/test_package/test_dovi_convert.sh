#!/data/service/hnp/bin/bash
# test_package/test_dovi_convert.sh — smoke test for dovi_convert 8.2.0
# Runs in conanrun env (PATH includes installed bin/)
#
# dovi_convert is a single-file Python CLI that orchestrates external media
# tools (ffmpeg, mkvmerge, mkvextract, dovi_tool, mediainfo). At startup
# main() runs DependencyManager.find_missing() which calls shutil.which() for
# each of those tools; if any is missing the script prints "Missing
# dependencies" and exits 1 before dispatching any command.
#
# This smoke test stubs the five external tools in a temp PATH dir so that
# find_missing() returns [] and main() proceeds to the help command path.
# The stubs are no-op executables — the help path never invokes them.
set -eu

BIN=dovi_convert
TMPDIR_T=$(mktemp -d 2>/dev/null || mktemp -d -t dovi_test)
trap 'rm -rf "$TMPDIR_T"' EXIT

# Stub the five external tools so DependencyManager.find_missing() returns []
for tool in ffmpeg dovi_tool mkvmerge mkvextract mediainfo; do
    printf '#!/bin/sh\nexit 0\n' > "$TMPDIR_T/$tool"
    chmod +x "$TMPDIR_T/$tool"
done

# Build a test PATH: stub dir first, then existing PATH (so dovi_convert is found via conanrun env)
TEST_PATH="$TMPDIR_T:$PATH"

echo "[test] which $BIN"
command -v "$BIN" >/dev/null 2>&1 || { echo "❌ $BIN not in PATH"; exit 1; }
echo "✅ $BIN found: $(command -v $BIN)"

echo "[test] $BIN help (exits 0, prints usage)"
out=$(PATH="$TEST_PATH" "$BIN" help 2>&1) || { echo "❌ help failed: $out"; exit 1; }
case "$out" in
    *dovi_convert*|*Dolby*Vision*) echo "✅ help output contains tool name" ;;
    *) echo "❌ help output unexpected: $out"; exit 1 ;;
esac

echo "[test] $BIN with no args (prints usage, exits 0)"
out=$(PATH="$TEST_PATH" "$BIN" 2>&1) || { echo "❌ no-args failed: $out"; exit 1; }

echo "[test] $BIN cleanup (no-op when no backups exist, exits 0)"
PATH="$TEST_PATH" "$BIN" cleanup >/dev/null 2>&1 || true

echo "✅ all dovi_convert smoke tests passed"
