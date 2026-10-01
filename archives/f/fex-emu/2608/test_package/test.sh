#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for the packaged fex-emu 2608 tools.
#
# Runs inside the conanrun environment, so PATH already points at the package
# bin/ directory.
set -euo pipefail

echo "[step] FEXGetConfig reports its usage"
getconfig_help="$(FEXGetConfig --help 2>&1)"
if ! grep -q "Usage: FEXGetConfig" <<<"$getconfig_help"; then
  echo "        [fail] FEXGetConfig --help did not report its usage"
  exit 1
fi
echo "        [ok] FEXGetConfig --help is functional"

echo "[step] FEXGetConfig resolves the installed prefix"
install_prefix="$(FEXGetConfig --install-prefix 2>&1)"
if [ -z "$install_prefix" ] || [ ! -d "$install_prefix" ]; then
  echo "        [fail] FEXGetConfig --install-prefix returned '$install_prefix'"
  exit 1
fi
echo "        [ok] FEXGetConfig --install-prefix -> $install_prefix"

echo "[step] FEXOfflineCompiler reports its usage"
# Note: FEXOfflineCompiler exits non-zero after printing --help (upstream
# behaviour), so only the output is asserted here.
offline_help="$(FEXOfflineCompiler --help 2>&1 || true)"
if ! grep -q "Usage: FEXOfflineCompiler" <<<"$offline_help"; then
  echo "        [fail] FEXOfflineCompiler --help did not report its usage"
  exit 1
fi
echo "        [ok] FEXOfflineCompiler --help is functional"

echo "[step] The emulator binaries are packaged as AArch64 ELF executables"
for tool in FEX FEXServer FEXBash FEXpidof; do
  tool_path="$(command -v "$tool")"
  if [ -z "$tool_path" ]; then
    echo "        [fail] $tool is not on PATH"
    exit 1
  fi
  # e_ident magic (7f 45 4c 46) followed by e_machine 0xb7 (AArch64, little endian).
  header="$(dd if="$tool_path" bs=1 count=20 2>/dev/null | od -An -tx1 | tr -d ' \n')"
  if [ "${header:0:8}" != "7f454c46" ]; then
    echo "        [fail] $tool is not an ELF file"
    exit 1
  fi
  if [ "${header:36:4}" != "b700" ]; then
    echo "        [fail] $tool is not an AArch64 executable (e_machine=${header:36:4})"
    exit 1
  fi
  echo "        [ok] $tool is an AArch64 ELF ($tool_path)"
done

echo "        [ok] fex-emu consumer smoke test passed"
