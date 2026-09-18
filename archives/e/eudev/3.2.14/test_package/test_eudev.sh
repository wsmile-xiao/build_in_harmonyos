#!/bin/sh
# eudev test_package 真实测试脚本（L0c 要求 test_package 有真实测试源文件）
# 用法: test_eudev.sh <pkg_dir>
#
# 校验 eudev 包可用（真实执行，R34 反空壳）：
#   ① 定位 udevadm（bin/ 或 sbin/）
#   ② `udevadm --version` 输出 ud**协议版本**（本版本为 251，对应 systemd 251）
#      —— 注意：这不是 eudev 包版本 3.2.14，两者不同，早年易误判
#   ③ `udevadm --help` 输出用法（证明工具真能运行，而非仅 --version 短路）
#   ④ libudev.so 已安装（apt 的 find_package(Udev) 需要它）
set -euo pipefail

PKG="${1:-}"
if [ -z "$PKG" ] || [ ! -d "$PKG" ]; then
    echo "FAIL: pkg dir not provided or missing: '$PKG'" >&2
    exit 1
fi

# ② udev 协议版本（udevadm --version 报的是它，非包版本）
EXPECT_UDEV_VER="251"

# ① 定位 udevadm
UDEVADM=""
for d in bin sbin; do
    if [ -x "$PKG/$d/udevadm" ]; then
        UDEVADM="$PKG/$d/udevadm"
        break
    fi
done
if [ -z "$UDEVADM" ]; then
    echo "FAIL: udevadm not found in $PKG/bin or $PKG/sbin" >&2
    exit 1
fi
echo "OK: udevadm found → $UDEVADM"

# ② --version
OUT="$("$UDEVADM" --version 2>&1)" || {
    echo "FAIL: udevadm --version 退出非零: $OUT" >&2
    exit 1
}
case "$OUT" in
    *"$EXPECT_UDEV_VER"*) : ;;
    *) echo "FAIL: udevadm --version 未报出 udev 协议版本 $EXPECT_UDEV_VER: $OUT" >&2; exit 1 ;;
esac
echo "OK: udevadm --version → $OUT (udev 协议版本)"

# ③ --help（证明工具真能运行）
HOUT="$("$UDEVADM" --help 2>&1)" || {
    echo "FAIL: udevadm --help 退出非零" >&2
    exit 1
}
case "$HOUT" in
    *udevadm*) : ;;
    *) echo "FAIL: udevadm --help 输出异常" >&2; exit 1 ;;
esac
echo "OK: udevadm --help 正常输出用法"

# ④ libudev（消费者链接的库）
LIB=""
for f in "$PKG"/lib/libudev.so*; do
    [ -e "$f" ] || continue
    case "$f" in
        *.so|*.so.*) LIB="$f"; break ;;
    esac
done
if [ -z "$LIB" ]; then
    echo "FAIL: libudev.so 未安装（apt 的 find_package(Udev) 需要它）" >&2
    exit 1
fi
echo "OK: libudev present → $(basename "$LIB")"

echo "eudev test_package PASS (udev 协议版本 $EXPECT_UDEV_VER)"
exit 0
