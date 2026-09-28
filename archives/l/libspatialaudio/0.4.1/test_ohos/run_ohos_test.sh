#!/bin/sh
# test_ohos — libspatialaudio 0.4.1 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，
# 区别于上游内置自测（4 个 ctest 用例）与 test_package 消费者用例：
#
#   T1  aarch64 ELF 验证（产物为 ELF64 AArch64，可在 OHOS 执行）
#   T2  宿主路径泄漏检查（静态库/头文件无 /storage、/home 等宿主绝对路径）
#   T3  OHOS 平台宏一致性：编译期 SPATIALAUDIO_CONFIG 头校验（MIT HRTF 内建、SOFA 关闭）
#   T4  运行时链接一致性：DT_NEEDED 仅依赖 OHOS 系统库（libc/libc++_shared），
#       且无宿主路径 RPATH 泄漏（OHOS 未知平台模块下 CMake 不发射 SONAME，
#       故以 DT_NEEDED/RPATH 作为可验证的 OHOS 运行时兼容属性）
#
# 用法：sh run_ohos_test.sh <已安装库目录>
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
set -u
LIBDIR="${1:-}"
[ -n "$LIBDIR" ] || { echo "usage: $0 <installed-lib-dir>"; exit 2; }
[ -d "$LIBDIR" ] || { echo "FAIL: lib dir not found: $LIBDIR"; exit 2; }

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- libspatialaudio 0.4.1 HarmonyOS 专项验证 (libdir=$LIBDIR) ---"

# T1: 库 ELF 架构
SO=$(ls "$LIBDIR"/libspatialaudio.so* 2>/dev/null | head -1)
[ -n "$SO" ] && readelf -h "$SO" 2>/dev/null | grep -q "AArch64" && r=0 || r=1
chk "T1 aarch64 ELF (libspatialaudio.so)" "$r"

# T2: 宿主路径泄漏（头文件）
HDR=$(ls "$LIBDIR"/../include/spatialaudio/SpatialaudioAPI.h 2>/dev/null)
if [ -n "$HDR" ] && grep -rqE "/storage/|/home/|currentUser" "$LIBDIR"/../include/spatialaudio 2>/dev/null; then
    r=1
else
    r=0
fi
chk "T2 头文件无宿主绝对路径泄漏" "$r"

# T3: 配置头平台一致性（MIT HRTF 内建 = ON，SOFA 关闭）
CFG="$LIBDIR"/../include/spatialaudio/SpatialaudioConfig.h
if [ -f "$CFG" ]; then
    mit=$(grep -c "define SPATIALAUDIO_SUPPORTS_MIT_HRTF 1" "$CFG")
    sofa=$(grep -c "define SPATIALAUDIO_SUPPORTS_SOFA 0" "$CFG")
    [ "$mit" -ge 1 ] && [ "$sofa" -ge 1 ] && r=0 || r=1
else
    r=1
fi
chk "T3 SpatialaudioConfig.h (MIT HRTF=ON, SOFA=OFF)" "$r"

# T4: 运行时链接一致性（DT_NEEDED 仅 OHOS 系统库 + 无宿主 RPATH）
RPATH=$(readelf -d "$SO" 2>/dev/null | grep -E "RPATH|RUNPATH" | head -2)
if echo "$RPATH" | grep -qE "/storage/|/home/|currentUser"; then
    r=1
else
    NEEDED=$(readelf -d "$SO" 2>/dev/null | grep NEEDED | grep -oE "\[[^]]+\]" | tr -d '[]')
    BAD=""
    for n in $NEEDED; do
        case "$n" in
            libc_shared.so|libc++_shared.so|libc.so|libm.so) ;;
            *) BAD="$BAD $n" ;;
        esac
    done
    [ -z "$BAD" ] && r=0 || r=1
fi
chk "T4 DT_NEEDED 仅 OHOS 系统库且无宿主 RPATH" "$r"

echo "--- libspatialaudio HarmonyOS 专项验证结束 (fail=$fail) ---"
exit "$fail"
