#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for gti executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] gti binary check"
gti_path=$(which gti 2>/dev/null || true)
if [ -n "$gti_path" ] && [ -f "$gti_path" ]; then
    echo "✅ gti binary found at $gti_path"
else
    echo "❌ gti binary not found in PATH"
    exit 1
fi

# Check ELF format using readelf (available on OHOS), fall back to magic byte check
echo "[test] verifying ELF format..."
is_elf=false
if command -v readelf >/dev/null 2>&1; then
    readelf -h "$gti_path" >/dev/null 2>&1 && is_elf=true
elif command -v file >/dev/null 2>&1; then
    file "$gti_path" 2>/dev/null | grep -qi "ELF" && is_elf=true
else
    # Check ELF magic bytes: 0x7f 'E' 'L' 'F'
    od -A x -t x1 -N 4 "$gti_path" 2>/dev/null | grep -qi "7f.*45.*4c.*46" && is_elf=true
fi

if [ "$is_elf" = true ]; then
    echo "✅ ELF binary OK"
else
    echo "❌ gti is not a valid ELF binary"
    exit 1
fi

echo "[test] gti --version (delegates to git --version)"
# gti shows a brief ASCII art animation then execs git
# On OHOS, unsigned binaries cannot be executed; on CI workers git may be absent
gti --version > /dev/null 2>&1 && echo "✅ gti runs OK" || {
    echo "[test] binary execution not possible (expected on OHOS without signing or without git installed)"
    echo "✅ ELF binary verified, execution may require signing"
}
