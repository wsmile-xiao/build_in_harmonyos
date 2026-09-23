#!/bin/sh
# test_ohos.sh — libotf/0.9.16 鸿蒙（OHOS aarch64）平台特有测试（1 用例，独立统计）
#
# 用法（由 test_package/conanfile.py 以 bash 调用）：
#   test_ohos.sh <conan-package-folder> <consumer-executable>
#
# 只检查 Conan 包内安装产物，不触碰源码/构建目录；任一断言失败即非零退出，
# 不做静默跳过（readelf 缺失直接判失败而非跳过）。
#
# 断言（同一用例内的多项检查，不拆分计数）：
#   A 安装产物齐备：lib/libotf.so.1、include/otf.h、bin/ 三个工具、lib/pkgconfig
#   B 架构契约：库/三个工具/消费者均为 ELF64 + AArch64
#   C SONAME == libotf.so.1
#   D NEEDED 含 libfreetype.so.6 —— 本次适配核心修复点：上游经已移除的
#     freetype-config 探测 freetype（FreeType ≥2.10 移除该脚本），探测失败时
#     libotf 不链接 freetype，FT_Load_Sfnt_Table 等符号悬空、OTF 表读取全失效
#   E NEEDED 无桌面图形库污染（libGL/libX11/libfontconfig/Xft 等）
#   F .codesign 段存在（OHOS ELF 签名要求，E212）
#   G 消费者可执行文件 NEEDED 含本库 SONAME（动态链接契约）
#   H include/otf.h 保留 <ft2build.h>/FT_FREETYPE_H 引用（recipe 声明
#     transitive_headers/transitive_libs 的依据：公开头文件泄漏 freetype 依赖）
#   I lib/pkgconfig/libotf.pc 含 -lotf（安装的 pkg-config 元数据可用）
set -u

if [ $# -lt 2 ]; then
	echo "usage: $0 <conan-package-folder> <consumer-executable>" >&2
	exit 2
fi

PKG="$1"
CONSUMER="$2"
FAIL=0
ok()  { echo "ok: $*"; }
bad() { FAIL=$((FAIL + 1)); echo "TEST FAIL: $*" >&2; }

# readelf 定位（OHOS 工具链 llvm-readelf 或 binutils readelf）
RE="$(command -v readelf || command -v llvm-readelf || true)"
if [ -z "$RE" ]; then
	echo "TEST FAIL: 未找到 readelf/llvm-readelf，无法校验 ELF 契约" >&2
	exit 1
fi

LIB="$PKG/lib/libotf.so.1"
HDR="$PKG/include/otf.h"
PC="$PKG/lib/pkgconfig/libotf.pc"
TOOLS="otfdump otflist otftobdf"

# ── A 安装产物齐备 ──
missing=""
for f in "$LIB" "$HDR" "$PC"; do
	[ -f "$f" ] || missing="$missing $f"
done
for t in $TOOLS; do
	[ -x "$PKG/bin/$t" ] || missing="$missing bin/$t"
done
if [ -z "$missing" ]; then
	ok "A 安装产物齐备（lib/include/bin×3/pkgconfig）"
else
	bad "A 安装产物缺失:$missing"
fi

# ── B 架构契约（ELF64 + AArch64）──
badarch=""
for f in "$LIB" "$PKG/bin/otfdump" "$PKG/bin/otflist" "$PKG/bin/otftobdf" "$CONSUMER"; do
	[ -f "$f" ] || { badarch="$badarch $f(不存在)"; continue; }
	h="$("$RE" -h "$f" 2>/dev/null || true)"
	echo "$h" | grep -q 'ELF64'   || badarch="$badarch $f(非ELF64)"
	echo "$h" | grep -q 'AArch64' || badarch="$badarch $f(非AArch64)"
done
if [ -z "$badarch" ]; then
	ok "B 库/三个工具/消费者均为 ELF64 + AArch64"
else
	bad "B 架构不符:$badarch"
fi

# ── C SONAME ──
SONAME="$("$RE" -d "$LIB" 2>/dev/null | grep SONAME | grep -o 'libotf\.so\.[0-9]*' | head -1)"
if [ "$SONAME" = "libotf.so.1" ]; then
	ok "C SONAME == libotf.so.1"
else
	bad "C SONAME 异常: [${SONAME:-空}]"
fi

# ── D NEEDED 含 freetype（适配核心修复点）──
if "$RE" -d "$LIB" 2>/dev/null | grep NEEDED | grep -q 'libfreetype\.so'; then
	ok "D NEEDED 含 libfreetype.so（freetype 探测修复生效）"
else
	bad "D NEEDED 缺 freetype: $("$RE" -d "$LIB" 2>/dev/null | grep NEEDED | tr -s ' ' | tr '\n' ' ')"
fi

# ── E NEEDED 无桌面图形库污染 ──
POLL="$({ "$RE" -d "$LIB"; for t in $TOOLS; do "$RE" -d "$PKG/bin/$t"; done; } 2>/dev/null \
	| grep NEEDED | grep -oE 'lib(GL|X11|fontconfig|Xft|xcb|xrender|xext)\.so[^ ]*' | sort -u | tr '\n' ' ')"
if [ -z "$POLL" ]; then
	ok "E NEEDED 无桌面图形库污染"
else
	bad "E NEEDED 污染: $POLL"
fi

# ── F .codesign 段（OHOS 平台签名）──
NCODESIGN="$("$RE" -SW "$LIB" 2>/dev/null | grep -c '\.codesign')"
if [ "$NCODESIGN" -ge 1 ]; then
	ok "F .codesign 段存在（OHOS 平台签名）"
else
	bad "F 缺少 .codesign 段"
fi

# ── G 消费者链接契约 ──
if [ -n "$SONAME" ] && "$RE" -d "$CONSUMER" 2>/dev/null | grep NEEDED | grep -q "$SONAME"; then
	ok "G 消费者 NEEDED 含 $SONAME（动态链接契约）"
else
	bad "G 消费者 NEEDED 未含 ${SONAME:-未知 SONAME}"
fi

# ── H 公开头文件的 freetype 依赖引用 ──
if grep -q 'ft2build\.h' "$HDR" && grep -q 'FT_FREETYPE_H' "$HDR"; then
	ok "H include/otf.h 保留 <ft2build.h>/FT_FREETYPE_H 引用（transitive_headers 依据）"
else
	bad "H include/otf.h 缺少 freetype 头引用"
fi

# ── I 安装的 pkg-config 元数据 ──
if grep -q '\-lotf' "$PC"; then
	ok "I lib/pkgconfig/libotf.pc 含 -lotf"
else
	bad "I lib/pkgconfig/libotf.pc 缺少 -lotf"
fi

if [ "$FAIL" -eq 0 ]; then
	echo "ALL TESTS PASSED (test_ohos.sh: 1 用例 / 9 断言)"
	exit 0
fi
echo "TEST OHOS FAILED (失败断言 $FAIL 项)" >&2
exit 1
