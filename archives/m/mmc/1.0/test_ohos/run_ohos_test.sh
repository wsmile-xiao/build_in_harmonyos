#!/bin/sh
# test_ohos — mmc 1.0 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS, musl libc, clang 15）上对最终 Conan 包做独立专项检查，
# 区别于上游样例（examples/*）与 test_package 消费者用例：
#
#   T1  aarch64 ELF 验证（ELF64 AArch64 可执行文件）
#   T2  宿主/构建机绝对路径泄漏检查（/storage /home /Users 不得进入产物）
#   T3  可移植性 RUNPATH 检查（不得嵌入构建机 SDK 路径，如 /data/service/hnp/ohos-sdk.org）
#   T4  OHOS 上真实运行：25 个四面体×40 网格的光子输运仿真，产出 flux 文件
#
# 用法：sh run_ohos_test.sh <已安装 mmc 二进制路径> [mesh 所在目录]
# 退出码：0=全部通过；非 0=有失败（打印首个错误）
set -u
BIN="${1:-}"
MESHDIR="${2:-$(dirname "$0")/../test_package}"
[ -n "$BIN" ] || { echo "usage: $0 <binary> [meshdir]"; exit 2; }
[ -f "$BIN" ] || { echo "FAIL: binary not found: $BIN"; exit 2; }

fail=0
chk() { if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi; }

echo "--- mmc 1.0 HarmonyOS 专项验证 (binary=$BIN) ---"

# T1: aarch64 ELF
readelf -h "$BIN" 2>/dev/null | grep -q "AArch64" && r=0 || r=1
chk "T1 aarch64 ELF (ELF64 AArch64)" "$r"

# T2: 宿主路径泄漏（构建机 /storage /home /Users 绝对路径不得进入产物）
if strings "$BIN" | grep -qE '/storage/|/home/|/Users/'; then
    echo "  leak: $(strings "$BIN" | grep -E '/storage/|/home/|/Users/' | head -1)"
    chk "T2 无宿主绝对路径泄漏" 1
else
    chk "T2 无宿主绝对路径泄漏" 0
fi

# T3: 构建机 SDK RUNPATH（上游 `make omp` 会把 /data/service/hnp/.../llvm/lib 烤进 RUNPATH，
#     使产物离开构建机后无法加载 libomp -> 配方选用 release 目标，必须无此 RUNPATH）
if readelf -d "$BIN" 2>/dev/null | grep -qE 'RUNPATH|RPATH'; then
    echo "  rpath: $(readelf -d "$BIN" 2>/dev/null | grep -E 'RUNPATH|RPATH' | head -1)"
    chk "T3 无构建机 RUNPATH" 1
else
    chk "T3 无构建机 RUNPATH" 0
fi

# T4: OHOS 上真实运行
WORK="$(mktemp -d 2>/dev/null || echo /storage/Users/currentUser/tmp/mmc-ohos-test)"
mkdir -p "$WORK"
cp "$MESHDIR"/node_minicube.dat "$MESHDIR"/elem_minicube.dat "$MESHDIR"/facenb_minicube.dat \
   "$MESHDIR"/velem_minicube.dat "$MESHDIR"/prop_minicube.dat "$MESHDIR"/minicube.inp "$WORK"/ 2>/dev/null
out=$( cd "$WORK" && "$BIN" -f minicube.inp -s minicube -n 100000 -b 1 -D TP 2>&1 ); rc=$?
if [ "$rc" = "0" ] && echo "$out" | grep -q "total simulated energy" && [ -s "$WORK/minicube.dat" ]; then
    chk "T4 OHOS 真实光子输运仿真 (rc=0, flux 输出)" 0
else
    echo "  rc=$rc"; echo "$out" | tail -3
    chk "T4 OHOS 真实光子输运仿真" 1
fi

echo "--- mmc 1.0 OHOS 专项: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail
