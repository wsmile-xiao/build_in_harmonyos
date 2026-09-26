#!/bin/bash
# HarmonyOS (鸿蒙特有) 测试：验证 kmerresistance 包内二进制面向 OpenHarmony 目标构建，
# 指针宽度与平台架构一致，且运行期动态依赖在 OHOS 环境下可闭合。
# 用法: test_ohos.sh <pkg_bin_dir>
#   <pkg_bin_dir> — 被测包 package_folder/bin（含 kmerresistance）
set -euo pipefail

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ]; then
    echo "ERROR: usage: test_ohos.sh <pkg_bin_dir>"
    exit 2
fi

fail() { echo "ERROR(HarmonyOS): $*"; exit 1; }

# --- 1. 平台断言：必须在 OpenHarmony 目标上执行 ---
case "$(param get const.ohos.fullname 2>/dev/null || true)" in
    OpenHarmony-*) echo "[ok] platform: $(param get const.ohos.fullname)" ;;
    *) fail "this test must run on an OpenHarmony target" ;;
esac

KMRES="$BIN_DIR/kmerresistance"
[ -x "$KMRES" ] || fail "kmerresistance not found/executable at $KMRES"

# --- readelf 定位（HNP 工具链优先，fallback PATH）---
READELF=""
for cand in /data/service/hnp/bin/readelf /data/service/hnp/bin/llvm-readelf; do
    if [ -x "$cand" ]; then READELF="$cand"; break; fi
done
if [ -z "$READELF" ] && command -v readelf >/dev/null 2>&1; then
    READELF="$(command -v readelf)"
fi
[ -n "$READELF" ] || fail "readelf not found (HNP toolchain or PATH)"

HDR="$($READELF -h "$KMRES")"

# --- 2. 指针宽度/三元组断言：ELF64 + AArch64（OHOS 64 位目标）---
echo "$HDR" | grep -q "Class:.*ELF64" || fail "expected ELF64 (64-bit pointer width), got: $(echo "$HDR" | grep Class: || true)"
echo "$HDR" | grep -q "Machine:.*AArch64" || fail "expected EM_AARCH64 (aarch64-linux-ohos triplet), got: $(echo "$HDR" | grep Machine: || true)"
echo "[ok] ELF header: ELF64 / AArch64 (aarch64-linux-ohos)"

# --- 3. 动态依赖闭合：kmerresistance 的 DT_NEEDED 共享库（-lm 等）
#         在 OHOS 运行环境（conanrun env 注入 LD_LIBRARY_PATH）下均可解析 ---
NEEDED="$($READELF -d "$KMRES" 2>/dev/null | grep NEEDED | sed 's/.*\[\(.*\)\].*/\1/')" || true
[ -n "$NEEDED" ] || fail "no DT_NEEDED entries found in kmerresistance"

miss=0
while IFS= read -r lib; do
    case "$lib" in
        libc.so*|libm.so*|libdl.so*|ld-musl*) continue ;;  # 系统 musl 库
    esac
    found=""
    IFS=':' read -r -a DIRS <<< "${LD_LIBRARY_PATH:-}"
    for d in "${DIRS[@]}" /system/lib64 /vendor/lib64; do
        [ -n "$d" ] || continue
        if [ -e "$d/$lib" ]; then found="$d/$lib"; break; fi
    done
    if [ -z "$found" ]; then
        echo "ERROR(HarmonyOS): NEEDED lib not resolvable: $lib"
        miss=1
    fi
done <<< "$NEEDED"
[ "$miss" -eq 0 ] || fail "dynamic dependencies not closed on OHOS"
echo "[ok] dynamic dependency closure: all DT_NEEDED libs found (path scan)"

# --- 4. kmerresistance 在 OHOS 上实际执行成功（运行期二次确认，-v 打印版本退出 0）---
"$KMRES" -v >/dev/null 2>&1 || fail "kmerresistance -v failed to run on OHOS"
echo "[ok] runtime: kmerresistance -v executed successfully on OHOS"

echo "HarmonyOS-specific test passed (rule12: platform/triplet/dep-closure/runtime)"
