#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the j4-dmenu-desktop executable.
# Runs in the conanrun environment (PATH already contains the installed bin/).
set -euo pipefail

echo "[test] j4-dmenu-desktop --version"
version_out=$(j4-dmenu-desktop --version)
echo "$version_out"
case "$version_out" in
  *3.2*) echo "✅ --version reports 3.2" ;;
  *)     echo "❌ unexpected version output: $version_out"; exit 1 ;;
esac

echo "[test] j4-dmenu-desktop --help"
help_out=$(j4-dmenu-desktop --help 2>&1)
echo "✅ --help exit 0"

# The launcher must still advertise its core dmenu/XDG flags.
echo "$help_out" | grep -q -- "--dmenu"
echo "✅ --help documents --dmenu"

echo "✅ test_package j4-dmenu/3.2 passed"
