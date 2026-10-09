#!/bin/sh
# test_ohos — winregfs 0.8 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，区别于
# test_package 的消费者用例：
#
#   T1  产物为 ELF64 AArch64（可在 OHOS 执行）
#   T2  无宿主绝对路径泄漏（/storage、/home、/Users 不得进入产物）
#   T3  OHOS musl 线程取消兼容落地：pthread_cancel 等符号由本包提供（已定义），
#       且不存在未解析引用 —— 证明 E085 适配补丁真实生效
#   T4  在 OHOS 上真实遍历生成的 hive：fsck.winregfs 报告 clean
#
# 用法：sh run_ohos_test.sh <bindir>
# 退出码：0=全部通过；非 0=有失败（打印首个错误）
set -u
BIN="${1:-}"
[ -n "$BIN" ] || { echo "usage: $0 <bindir>"; exit 2; }
FSCK="$BIN/fsck.winregfs"
MOUNT="$BIN/mount.winregfs"
[ -f "$FSCK" ] || { echo "FAIL: fsck.winregfs not found: $FSCK"; exit 2; }
[ -f "$MOUNT" ] || { echo "FAIL: mount.winregfs not found: $MOUNT"; exit 2; }

fail=0
chk() { if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi; }

echo "--- winregfs HarmonyOS 专项验证 (bindir=$BIN) ---"

# T1: aarch64 ELF
readelf -h "$FSCK" 2>/dev/null | grep -q "AArch64" && r=0 || r=1
chk "T1 aarch64 ELF (ELF64 AArch64)" "$r"

# T2: 宿主路径泄漏
if strings "$FSCK" "$MOUNT" 2>/dev/null | grep -qE '/storage/|/home/|/Users/'; then
    echo "  leak: $(strings "$FSCK" "$MOUNT" 2>/dev/null | grep -E '/storage/|/home/|/Users/' | head -1)"
    chk "T2 无宿主绝对路径泄漏" 1
else
    chk "T2 无宿主绝对路径泄漏" 0
fi

# T3: OHOS pthread 取消兼容符号（由 mount.winregfs 提供定义，且无未解析引用）
#     libfuse.a 只在链接 mount.winregfs 时被引入，兼容层也因此只进入该二进制。
sym() { readelf -sW "$1" 2>/dev/null; }
t3=0
for symname in pthread_cancel pthread_setcancelstate pthread_testcancel; do
    def=$(sym "$MOUNT" | awk -v n="$symname" '$4=="FUNC" && $7!="UND" && $8==n' | wc -l)
    und=$(sym "$MOUNT" | awk -v n="$symname" '$4=="FUNC" && $7=="UND" && $8==n' | wc -l)
    if [ "$def" -lt 1 ] || [ "$und" -ne 0 ]; then
        echo "  $symname: defined=$def undefined=$und"
        t3=1
    fi
done
chk "T3 mount.winregfs 内 pthread_cancel/setcancelstate/testcancel 已定义且无未解析引用" "$t3"

# T4: 真实 hive 遍历（OHOS 本地执行）
WORK="$(pwd)/winregfs-ohos-work"
rm -rf "$WORK"; mkdir -p "$WORK"
PY=""
command -v python3 >/dev/null 2>&1 && PY=python3
[ -z "$PY" ] && command -v python >/dev/null 2>&1 && PY=python
[ -n "$PY" ] || { echo "FAIL: no python interpreter for mkhive.py"; exit 1; }
"$PY" mkhive.py "$WORK/h.hiv" >/dev/null || { echo "FAIL: hive generation"; exit 1; }
out=$("$FSCK" -v "$WORK/h.hiv" 2>&1); rc=$?
echo "$out" | grep -E "Keys:|is clean|errors"
[ "$rc" = "0" ] && echo "$out" | grep -q "is clean" && r=0 || r=1
chk "T4 OHOS 上 fsck 遍历生成 hive -> clean (exit=$rc)" "$r"
rm -rf "$WORK"

echo "--- winregfs OHOS 专项: $([ $fail = 0 ] && echo 'ALL PASS (4)' || echo FAILED) ---"
exit $fail
