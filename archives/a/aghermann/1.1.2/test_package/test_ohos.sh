#!/bin/bash
# HarmonyOS (鸿蒙特有) 测试：验证 aghermann 包内二进制面向 OpenHarmony 目标构建，
# 指针宽度与平台架构一致，且运行期动态依赖在 OHOS 环境下可闭合。
# 用法: test_ohos.sh <pkg_bin_dir> <minimal.edf>
#   <pkg_bin_dir>  — 被测包 package_folder/bin（含 edfhed / edfcat）
#   <minimal.edf>  — 2 通道 EDF 文件（由 conanfile.py test() 生成）
set -euo pipefail

BIN_DIR="${1:-}"
EDF_FILE="${2:-}"
if [ -z "$BIN_DIR" ] || [ -z "$EDF_FILE" ]; then
    echo "ERROR: usage: test_ohos.sh <pkg_bin_dir> <minimal.edf>"
    exit 2
fi

fail() { echo "ERROR(HarmonyOS): $*"; exit 1; }

# --- 1. 平台断言：必须在 OpenHarmony 目标上执行 ---
case "$(param get const.ohos.fullname 2>/dev/null || true)" in
    OpenHarmony-*) echo "[ok] platform: $(param get const.ohos.fullname)" ;;
    *) fail "this test must run on an OpenHarmony target" ;;
esac

EDFHED="$BIN_DIR/edfhed"
[ -x "$EDFHED" ] || fail "edfhed not found/executable at $EDFHED"

# --- readelf 定位（HNP 工具链优先，fallback PATH）---
READELF=""
for cand in /data/service/hnp/bin/readelf /data/service/hnp/bin/llvm-readelf; do
    if [ -x "$cand" ]; then READELF="$cand"; break; fi
done
if [ -z "$READELF" ] && command -v readelf >/dev/null 2>&1; then
    READELF="$(command -v readelf)"
fi
[ -n "$READELF" ] || fail "readelf not found (HNP toolchain or PATH)"

HDR="$($READELF -h "$EDFHED")"

# --- 2. 指针宽度/三元组断言：ELF64 + AArch64（OHOS 64 位目标 ---
echo "$HDR" | grep -q "Class:.*ELF64" || fail "expected ELF64 (64-bit pointer width), got: $(echo "$HDR" | grep Class: || true)"
echo "$HDR" | grep -q "Machine:.*AArch64" || fail "expected EM_AARCH64 (aarch64-linux-ohos triplet), got: $(echo "$HDR" | grep Machine: || true)"
echo "[ok] ELF header: ELF64 / AArch64 (aarch64-linux-ohos)"

# --- 3. 动态依赖闭合：edfhed 的 DT_NEEDED 共享库（libsigfile 等）
#         在 OHOS 运行环境（conanrun env 注入 LD_LIBRARY_PATH）下均可解析 ---
NEEDED="$($READELF -d "$EDFHED" 2>/dev/null | grep NEEDED | sed 's/.*\[\(.*\)\].*/\1/')" || true
[ -n "$NEEDED" ] || fail "no DT_NEEDED entries found in edfhed"

LDD=""
for cand in /data/service/hnp/bin/ldd /data/service/hnp/bin/llvm-ldd; do
    if [ -x "$cand" ]; then LDD="$cand"; break; fi
done
if [ -z "$LDD" ] && command -v ldd >/dev/null 2>&1; then
    LDD="$(command -v ldd)"
fi

if [ -n "$LDD" ]; then
    MISSING="$("$LDD" "$EDFHED" 2>/dev/null | grep -i "not found" || true)"
    if [ -n "$MISSING" ]; then
        fail "dynamic dependencies not closed on OHOS: $MISSING"
    fi
    echo "[ok] dynamic dependency closure: all $(echo "$NEEDED" | wc -l | tr -d ' ') DT_NEEDED libs resolve"
else
    # 无 ldd 时：对每个非 soname-占位的 NEEDED 项，检查 LD_LIBRARY_PATH 与系统库目录。
    # 注意：conan test_package 用 /bin/sh 执行本脚本（忽略 shebang），OHOS 的
    # /bin/sh 为 toybox，不支持 bash 数组（read -a / ${arr[@]} / <<<），旧实现
    # 静默拆不出 LD_LIBRARY_PATH 目录，误报 "NEEDED lib not resolvable"
    # （CI #59412/#59738 实测失败；二进制实际可运行，见 test_edf.sh）。
    # 改用 POSIX set -- 位置参数拆分，兼容 toybox sh。
    OLDIFS="$IFS"
    IFS=':'
    # shellcheck disable=SC2086
    set -- ${LD_LIBRARY_PATH:-}
    IFS="$OLDIFS"
    miss=0
    while IFS= read -r lib; do
        case "$lib" in
            libc.so*|libm.so*|libdl.so*|ld-musl*) continue ;;  # 系统 musl 库
        esac
        found=""
        for d in "$@" /system/lib64 /vendor/lib64; do
            [ -n "$d" ] || continue
            if [ -e "$d/$lib" ]; then found="$d/$lib"; break; fi
        done
        if [ -z "$found" ]; then
            echo "ERROR(HarmonyOS): NEEDED lib not resolvable: $lib"
            miss=1
        fi
    done <<EOF
$NEEDED
EOF
    [ "$miss" -eq 0 ] || fail "dynamic dependencies not closed on OHOS"
    echo "[ok] dynamic dependency closure: all DT_NEEDED libs found (path scan)"
fi

# --- 4. edfhed 在 OHOS 上实际解析成功（运行期二次确认）---
"$EDFHED" "$EDF_FILE" >/dev/null 2>&1 || fail "edfhed failed to run on OHOS"
echo "[ok] edfhed executed successfully on OpenHarmony"

echo "[ok] HarmonyOS-specific test passed (platform triplet / pointer width / dep closure)"
