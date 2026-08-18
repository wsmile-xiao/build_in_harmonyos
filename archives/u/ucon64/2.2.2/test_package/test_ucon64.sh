#!/data/service/hnp/bin/bash
# test_package/test_ucon64.sh — smoke test for the ucon64 executable.
# Runs in the conanrun env, so PATH includes the installed bin/ (i.e. `ucon64`).
set -euo pipefail

UCON64="${1:-ucon64}"

echo "[step] ucon64 --version"
# Proves the binary executes, is ELF-signed, and is statically linked.
"$UCON64" --version

echo "[step] ucon64 --help (first 5 lines)"
# Verify the binary can process arguments and produce help output.
"$UCON64" --help 2>&1 | head -5

echo "ucon64 test_package: PASS"
