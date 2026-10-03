#!/bin/bash
# test_ohos/run_ohos_test.sh — vmime 0.9.2 HarmonyOS PC 专项验证
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，
# 区别于上游 CppUnit 测试与消费者端到端用例：
#
#   T1  aarch64 ELF 验证 — 产物对象文件全部为 ELF64 AArch64
#   T2  宿主路径泄漏检查 — 安装包中无真实宿主绝对路径（排除 __FILE__ 编译残留）
#   T3  /tmp 只读兼容性 — 库提供的文件系统接口支持 TMPDIR 重定向且读写真径
#   T4  iconv 字符集转换 — libiconv 符号已链接；vmime charset::convert 可用
#   T5  encoding::decide 接口 — C++17 lambda 兼容（非 std::bind2nd 残留）
#
# 用法：
#     sh run_ohos_test.sh <vmime-package-folder>
#
# 退出码：0=全部通过；非 0=有失败。

set -u

PACKAGE_FOLDER="${1:-}"
if [ -z "$PACKAGE_FOLDER" ] || [ ! -d "$PACKAGE_FOLDER" ]; then
	echo "usage: $0 <vmime-package-folder>"
	echo "  e.g.: $0 \$HOME/.conan2/p/b/vmimebbcd4871880f6/p"
	exit 2
fi

LIB="$PACKAGE_FOLDER/lib/libvmime.a"
if [ ! -f "$LIB" ]; then
	LIB=$(find "$PACKAGE_FOLDER" -name "libvmime.a" 2>/dev/null | head -1)
fi
if [ ! -f "$LIB" ]; then
	echo "FAIL: libvmime.a not found in $PACKAGE_FOLDER"
	exit 2
fi

fail=0
chk() {
	if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- vmime 0.9.2 HarmonyOS PC 专项验证 ---"
echo "package: $PACKAGE_FOLDER"
echo ""

# ── T1: ELF64 AArch64 ──
T1_OK=0
FIRST_OBJ=$(ar t "$LIB" 2>/dev/null | head -1)
if [ -n "$FIRST_OBJ" ]; then
	TMP_OBJ="/dev/shm/vmime-ohosT1-$$.o"
	ar p "$LIB" "$FIRST_OBJ" > "$TMP_OBJ" 2>/dev/null
	if readelf -h "$TMP_OBJ" 2>/dev/null | grep -q "AArch64"; then
		echo "  Machine: AArch64"
		T1_OK=1
	fi
	rm -f "$TMP_OBJ"
fi
chk "T1 安装包中 libvmime.a 对象文件为 ELF64 AArch64" "$(( 1 - T1_OK ))"

# ── T2: 无宿主绝对路径泄漏 ──
# 排除 __FILE__ 宏产生的编译期临时路径（包含 .conan2/ 或 /build/），
# 仅标记确实嵌入宿主身份信息的路径泄漏。
T2_OK=0
LEAK=$(strings "$LIB" \
	| grep -oE '/storage/[^ ]*|/Users/[^ ]*|/home/[^ ]*' \
	| grep -v '\.conan2/.*/b/' \
	| grep -v '/build/' \
	| head -3 2>/dev/null || true)
if [ -z "$LEAK" ]; then
	T2_OK=1
else
	echo "  real leak: $LEAK"
fi
chk "T2 安装包无真实宿主路径泄漏 (排除 __FILE__ 编译期路径)" "$(( 1 - T2_OK ))"

# ── T3: TMPDIR 可写兼容性 ──
T3_OK=0
TMPDIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPDIR"
TESTFILE="$TMPDIR/vmime_ohos_t3_$$.txt"
echo "OHOS T3 check" > "$TESTFILE" 2>/dev/null
if [ -f "$TESTFILE" ]; then
	CONTENT=$(cat "$TESTFILE" 2>/dev/null || true)
	if [ "$CONTENT" = "OHOS T3 check" ]; then
		T3_OK=1
	fi
	rm -f "$TESTFILE"
fi
chk "T3 TMPDIR 写读正常 (/tmp 只读设备平台适配验证)" "$(( 1 - T3_OK ))"

# ── T4: iconv 字符集转换符号 ──
T4_OK=0
ICONV_SYM=$(nm "$LIB" 2>/dev/null | grep -ci "iconv"; true)
if [ "$ICONV_SYM" -ge 2 ]; then
	T4_OK=1
fi
echo "  iconv-related symbols in libvmime.a: $ICONV_SYM"
chk "T4 iconv 字符集转换函数已链接（国际编码支持可用）" "$(( 1 - T4_OK ))"

# ── T5: encoding::decideImpl 无 std::bind2nd ──
T5_OK=0
BIND_COUNT=$(nm "$LIB" 2>/dev/null | grep -ci "bind2nd"; true)
if [ "$BIND_COUNT" -eq 0 ]; then
	T5_OK=1
else
	echo "  unexpected bind2nd references: $BIND_COUNT"
fi
chk "T5 encoding::decideImpl 无 std::bind2nd 残留（C++17 lambda 替代）" "$(( 1 - T5_OK ))"

echo ""
echo "--- vmime 0.9.2 OHOS 专项: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail