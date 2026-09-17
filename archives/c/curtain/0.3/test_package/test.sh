#!/usr/bin/env bash
set -eu

package="${1:?usage: test.sh PACKAGE_DIR}"
check="$package/bin/curtain_check"
napi="$package/lib/libcurtain.so"
header="$package/include/curtain/curtain_core.h"
project="$package/share/curtain/harmony"

pass=0
fail=0

ok() {
    echo "PASS: $1"
    pass=$((pass + 1))
}

bad() {
    echo "FAIL: $1" >&2
    fail=$((fail + 1))
}

require_file() {
    if [ -s "$1" ]; then
        ok "$2"
    else
        bad "$2"
    fi
}

# 1-2: checker binary present and executable
if [ -x "$check" ]; then
    ok "curtain_check is present and executable"
else
    bad "curtain_check missing or not executable: $check"
fi

# 3-4: AArch64 ELF
magic=$(head -c 4 "$check" | od -An -tx1 | tr -d ' \n')
if [ "$magic" = "7f454c46" ]; then
    ok "curtain_check is an ELF binary"
else
    bad "curtain_check magic is $magic"
fi
machine=$(od -An -tu1 -j18 -N1 "$check" | tr -d ' ')
if [ "$machine" = "183" ]; then
    ok "curtain_check is AArch64 (e_machine 0xb7)"
else
    bad "curtain_check e_machine is $machine"
fi

# 5-7: regression checker runs and reports zero failures
output=$("$check" 2>&1) && rc=0 || rc=$?
echo "$output"
if [ "$rc" -eq 0 ]; then
    ok "curtain_check exit code 0"
else
    bad "curtain_check exit code $rc"
fi
case "$output" in
    *"0 failures"*) ok "curtain_check reports 0 failures" ;;
    *) bad "curtain_check did not report 0 failures" ;;
esac
case "$output" in
    *"checks,"*) ok "curtain_check reported a check count" ;;
    *) bad "curtain_check output missing check count" ;;
esac

# 8-10: NAPI module and its NAPI dependency
require_file "$napi" "libcurtain.so packaged"
if [ -s "$napi" ]; then
    readelf_bin=""
    for candidate in /data/service/hnp/bin/llvm-readelf \
                     /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-readelf; do
        if [ -x "$candidate" ]; then
            readelf_bin=$candidate
            break
        fi
    done
    if [ -z "$readelf_bin" ]; then
        readelf_bin=$(command -v llvm-readelf || command -v readelf || true)
    fi
    if [ -n "$readelf_bin" ]; then
        if "$readelf_bin" -d "$napi" | grep -q 'libace_napi.z.so'; then
            ok "libcurtain.so NEEDED contains libace_napi.z.so"
        else
            bad "libcurtain.so does not link libace_napi.z.so"
        fi
    else
        echo "WARN: no readelf found, skipping NEEDED check"
    fi
fi
require_file "$header" "curtain_core.h packaged"

# 11-15: ArkUI host project payload
require_file "$project/CMakeLists.txt" "harmony CMakeLists.txt packaged"
require_file "$project/project/entry/src/main/ets/pages/Curtain.ets" "harmony-project Curtain.ets packaged"
require_file "$project/project/entry/src/main/cpp/curtain_core.c" "harmony-project curtain_core.c packaged"
require_file "$project/project/entry/src/main/module.json5" "harmony-project module.json5 packaged"
require_file "$project/project/entry/src/main/resources/rawfile/curtain.png" "harmony-project curtain.png packaged"

# 16-17: licenses and upstream ui resources
require_file "$package/licenses/curtain/COPYING" "upstream COPYING license packaged"
require_file "$package/share/curtain/ui/curtain.glade" "upstream curtain.glade packaged"

echo "curtain test_package: $pass passed, $fail failed"
if [ "$fail" -ne 0 ]; then
    exit 1
fi
echo "Installed Curtain core, NAPI module, ArkUI host project and licenses verified"
