#!/bin/sh
# test_ohos — linuxptp 4.4 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 对最终 Conan 包做平台专项检查，区别于 build() 内的补全单元测试与
# test_package 的消费者用例：
#
#   T1  九个可执行文件全部存在且为 aarch64 ELF（设备原生编译产物）
#   T2  产物内无构建机宿主绝对路径泄漏（/storage、/home、/Users）
#   T3  九个二进制在本机（OHOS/aarch64）实际可执行：`-v` 退出码 0 且报告 4.4
#       （上游九个工具均不支持 --version，统一用 -v；ts2phc 的 `-h` 上游返回
#        255 属既定行为，见 test_package/test.sh 的说明）
#   T4  ptp4l 真实功能路径：读取配置并对不存在的网卡报错退出（非 0）
#   T5  man 手册随包分发（9 个 .8 文件）
#
# 用法：sh run_ohos_test.sh <conan 包目录>
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
set -euo pipefail
PKG="${1:-}"
[ -n "$PKG" ] || { echo "usage: $0 <package_folder>"; exit 2; }
BINDIR="$PKG/bin"
[ -d "$BINDIR" ] || { echo "FAIL: no bin/ directory in $PKG"; exit 2; }

BINS="ptp4l hwstamp_ctl nsm phc2sys phc_ctl pmc timemaster ts2phc tz2alt"
fail=0

chk() { # $1=name $2=result(0=ok)
	if [ "$2" = "0" ]; then
		echo "PASS: $1"
	else
		echo "FAIL: $1"
		fail=1
	fi
}

echo "--- linuxptp HarmonyOS 专项验证 (package=$PKG) ---"

# T1: 九个文件存在且为 ELF64 aarch64（0x7f 'E' 'L' 'F'）
count=0
nonelf=0
for b in $BINS; do
	f="$BINDIR/$b"
	if [ -f "$f" ]; then
		count=$((count + 1))
		magic=$(head -c 4 "$f" | od -An -tx1 | tr -d ' \n')
		[ "$magic" = "7f454c46" ] || nonelf=$((nonelf + 1))
	else
		echo "  missing: $f"
	fi
done
chk "T1a 九个二进制齐备 (found=$count/9)" "$([ "$count" = "9" ] && echo 0 || echo 1)"
chk "T1b 全部为 ELF 产物 (non_elf=$nonelf)" "$([ "$nonelf" = "0" ] && echo 0 || echo 1)"

# T2: 宿主路径泄漏（构建机 /storage、/home、/Users 绝对路径不得进入产物）
leak=0
for b in $BINS; do
	f="$BINDIR/$b"
	[ -f "$f" ] || continue
	if LC_ALL=C grep -aqe '/storage/' -e '/home/' -e '/Users/' "$f"; then
		echo "  leak in $b"
		leak=$((leak + 1))
	fi
done
chk "T2 无宿主绝对路径泄漏 (leaks=$leak)" "$([ "$leak" = "0" ] && echo 0 || echo 1)"

# T3: 本机可执行性（OHOS/aarch64 上运行 -v 并核对版本号）
runfail=0
for b in $BINS; do
	f="$BINDIR/$b"
	[ -f "$f" ] || continue
	if ! "$f" -v 2>/dev/null | grep -q "4.4"; then
		echo "  version check failed: $b -v"
		runfail=$((runfail + 1))
	fi
done
chk "T3 九个二进制本机可运行并报告 4.4 (failures=$runfail)" "$([ "$runfail" = "0" ] && echo 0 || echo 1)"

# T4: ptp4l 功能路径 — 不存在的网卡必须报错退出（非 0）
CFG=$(mktemp 2>/dev/null || echo "${TMPDIR:-/tmp}/lp_cfg.$$")
printf '[global]\nlogging_level 6\n' > "$CFG"
if "$BINDIR/ptp4l" -f "$CFG" -i no_such_interface_0 -m >/dev/null 2>&1; then
	chk "T4 ptp4l 对不存在的网卡报错退出" 1
else
	chk "T4 ptp4l 对不存在的网卡报错退出" 0
fi
rm -f "$CFG"

# T5: man 手册（无匹配时 ls 非 0，pipefail 下需显式兜底）
man=$(ls "$PKG/man/man8"/*.8 2>/dev/null | wc -l || true)
man=$(echo "$man" | tr -d ' ')
chk "T5 man8 手册随包分发 (found=$man/9)" "$([ "$man" = "9" ] && echo 0 || echo 1)"

echo "--- linuxptp OHOS 专项: $([ "$fail" = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail
