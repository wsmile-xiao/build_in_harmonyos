#!/bin/sh
# test_ohos.sh — libdrawtext/0.6 鸿蒙（OHOS armv8）特有测试
# 独立统计的测试用例：只检查 Conan 包内安装产物，不触碰源码/构建目录。
#
# 用法（由 test_package/conanfile.py 调用）：
#   test_ohos.sh <conan-package-folder> <consumer-executable> [ld_library_path]
#
# 检查项（任一失败即非零退出，不静默跳过）：
#   1. 包内 lib/libdrawtext.so.0 存在（安装产物，非构建树）
#   2. readelf -h：ELF64 + AArch64
#   3. readelf -d：SONAME == libdrawtext.so.0
#   4. readelf -d：NEEDED 含 libfreetype.so.6
#   5. readelf -d：NEEDED 不含任何桌面 GL 库（NO_OPENGL 构建验证）
#   6. readelf -SW：存在恰好一个 .codesign 段（OHOS 签名要求，E212）
#   7. 运行直接链接的软件 raster 消费者：字体加载 + 软件光栅化 + 非零像素
set -u

if [ $# -lt 2 ]; then
	echo "usage: $0 <package-folder> <consumer-executable> [ld_library_path]" >&2
	exit 2
fi

PKG="$1"
CONSUMER="$2"
LDLP="${3:-}"

fail() { echo "OHOS-TEST FAIL: $*" >&2; exit 1; }
ok()   { echo "ohos ok: $*"; }

SO="$PKG/lib/libdrawtext.so.0"

# ── 1. 安装产物存在 ──
[ -f "$SO" ] || fail "missing installed $SO (Conan package product)"
ok "installed libdrawtext.so.0 present in package"

# ── readelf 工具定位（PATH 中优先 readelf，其次 llvm-readelf）──
RE="$(command -v readelf || command -v llvm-readelf || true)"
[ -n "$RE" ] || fail "no readelf/llvm-readelf available"

# ── 2. ELF 架构：ELF64 + AArch64 ──
# 传入的 PKG 即当前 OHOS armv8 profile 解析出的包目录（conanfile.py 传入
# self.dependencies["libdrawtext"].package_folder），故架构核对即归属核对。
HDR="$($RE -h "$SO")" || fail "readelf -h failed"
echo "$HDR" | grep -q "Class:.*ELF64" || fail "not ELF64: $(echo "$HDR" | grep Class:)"
echo "$HDR" | grep -q "Machine:.*AArch64" || fail "not AArch64: $(echo "$HDR" | grep Machine:)"
ok "ELF64 AArch64 (ohos-aarch64 profile package)"

# ── 3. SONAME ──
SONAME_LINE="$($RE -d "$SO" | grep 'SONAME' || true)"
echo "$SONAME_LINE" | grep -q 'libdrawtext.so.0' || fail "SONAME mismatch: ${SONAME_LINE:-<none>}"
ok "SONAME libdrawtext.so.0"

# ── 4. NEEDED 含 libfreetype.so.6（freetype 渲染后端依赖）──
$RE -d "$SO" | grep 'NEEDED' | grep -q 'libfreetype.so.6' \
	|| fail "NEEDED lacks libfreetype.so.6"
ok "NEEDED includes libfreetype.so.6"

# ── 5. NEEDED 不含桌面 GL（NO_OPENGL 构建）──
GL_SYMS="$($RE -d "$SO" | grep 'NEEDED' | grep -iE 'libGL|libGLU|GLEW|GLUT|libEGL|libOpenGL|libOSMesa' || true)"
[ -z "$GL_SYMS" ] || fail "desktop GL libraries in NEEDED: $GL_SYMS"
ok "no desktop GL in NEEDED (NO_OPENGL build)"

# ── 6. .codesign 段（OHOS 签名，E212 仓库既定方式）──
CODESIGN_N="$($RE -SW "$SO" | grep -c '\.codesign' || true)"
[ "$CODESIGN_N" -ge 1 ] || fail "no .codesign section in installed $SO"
ok ".codesign section present ($CODESIGN_N)"

# ── 7. 运行安装包链接的软件 raster 消费者（真实渲染）──
[ -x "$CONSUMER" ] || fail "consumer executable not found: $CONSUMER"
# 消费者自身也必须直接依赖 SONAME 库
$RE -d "$CONSUMER" | grep 'NEEDED' | grep -q 'libdrawtext.so.0' \
	|| fail "consumer NEEDED lacks libdrawtext.so.0"

if [ -n "$LDLP" ]; then
	OUT="$(LD_LIBRARY_PATH="$LDLP" "$CONSUMER" 2>&1)"
else
	OUT="$("$CONSUMER" 2>&1)"
fi
RC=$?
[ $RC -eq 0 ] || fail "software raster consumer exited $RC: $OUT"
echo "$OUT" | grep -q 'ALL TESTS PASSED' || fail "consumer did not pass: $OUT"
echo "$OUT" | grep -q 'nonzero pixels' || fail "consumer reported no pixel evidence: $OUT"
ok "software raster rendering works without desktop GL"
echo "$OUT" | sed -n 's/^/ohos   /p'

echo "OHOS TESTS PASSED"
exit 0
