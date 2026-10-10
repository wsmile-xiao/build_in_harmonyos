#!/usr/bin/env bash
# test_package/test_ohos/run_ohos_test.sh — verify the HarmonyOS PC ELF ABI.
set -euo pipefail

pd_bin="$(command -v pd)"
if command -v readelf >/dev/null 2>&1; then
    elf_tool=readelf
elif command -v llvm-readelf >/dev/null 2>&1; then
    elf_tool=llvm-readelf
else
    echo "FAIL: readelf or llvm-readelf is required for the HarmonyOS ABI check"
    exit 1
fi

header="$($elf_tool -h "$pd_bin")"
echo "$header" | grep -Eq 'Machine:.*AArch64' || {
    echo "FAIL: pd is not an AArch64 executable"
    exit 1
}

program_headers="$($elf_tool -l "$pd_bin")"
echo "$program_headers" | grep -q 'ld-musl-aarch64.so.1' || {
    echo "FAIL: pd does not use the HarmonyOS PC musl loader"
    exit 1
}

echo "PASS: AArch64 ELF uses ld-musl-aarch64.so.1"
