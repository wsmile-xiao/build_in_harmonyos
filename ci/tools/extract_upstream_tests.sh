#!/bin/bash
# ============================================================
# extract_upstream_tests.sh — 上游官方测试分析辅助脚本
#
# 用途: 自动分析上游源码包的 make check / ctest / meson test
#       测试列表，辅助填写 test_package/MANIFEST.yml
#
# 用法:
#   bash extract_upstream_tests.sh <源码包.tar.gz 或解压目录>
#
# 示例:
#   bash extract_upstream_tests.sh zlib-1.3.1.tar.gz
#   bash extract_upstream_tests.sh /path/to/bash-5.3
#
# 输出:
#   1. 检测到的构建系统
#   2. make -n check (dry run) 的测试命令列表
#   3. 涉及的测试源文件列表
#   4. MANIFEST.yml 的骨架模板（可直接复制使用）
# ============================================================
set -euo pipefail

# ── 参数检查 ──
if [ $# -lt 1 ]; then
    echo "用法: bash extract_upstream_tests.sh <源码包.tar.gz | 解压目录>"
    echo "示例:"
    echo "  bash extract_upstream_tests.sh zlib-1.3.1.tar.gz"
    echo "  bash extract_upstream_tests.sh /path/to/bash-5.3"
    exit 1
fi

INPUT="$1"
WORK_DIR="/tmp/upstream_test_analysis_$$"

cleanup() {
    [ -d "$WORK_DIR" ] && rm -rf "$WORK_DIR"
}
trap cleanup EXIT

# ── 解压或使用目录 ──
if [ -f "$INPUT" ] && echo "$INPUT" | grep -qE '\.(tar\.gz|tgz|tar\.bz2|tar\.xz|tar)$'; then
    echo "[step] 解压 $INPUT ..."
    mkdir -p "$WORK_DIR"
    tar xf "$INPUT" -C "$WORK_DIR"
    # 取解压后的顶层目录
    SRC_DIR=$(find "$WORK_DIR" -maxdepth 1 -mindepth 1 -type d -print -quit 2>/dev/null)
    SRC_DIR="${SRC_DIR%/}"
elif [ -d "$INPUT" ]; then
    SRC_DIR="$INPUT"
else
    echo "[error] $INPUT 既不是 tar 包也不是目录"
    exit 1
fi

if [ -z "$SRC_DIR" ] || [ ! -d "$SRC_DIR" ]; then
    echo "[error] 无法定位源码目录"
    exit 1
fi

PKG_NAME=$(basename "$SRC_DIR" | sed 's/-[0-9].*//')
PKG_VER=$(basename "$SRC_DIR" | sed "s/^${PKG_NAME}-//")

echo ""
echo "══════════════════════════════════════════"
echo " 上游测试分析报告"
echo " 包: ${PKG_NAME}/${PKG_VER}"
echo " 源码: $SRC_DIR"
echo "══════════════════════════════════════════"
echo ""

# ── 1. 检测构建系统 ──
echo "── [1] 构建系统检测 ──────────────────────"
BUILD_SYSTEM="unknown"
CHECK_CMD=""
if [ -f "$SRC_DIR/CMakeLists.txt" ]; then
    BUILD_SYSTEM="cmake"
    CHECK_CMD="ctest -N"
    echo "构建系统: CMake"
elif [ -f "$SRC_DIR/meson.build" ]; then
    BUILD_SYSTEM="meson"
    CHECK_CMD="meson test --list"
    echo "构建系统: Meson"
elif [ -f "$SRC_DIR/configure.ac" ] || [ -f "$SRC_DIR/configure.in" ]; then
    BUILD_SYSTEM="autotools"
    CHECK_CMD="make -n check"
    echo "构建系统: Autotools"
elif [ -f "$SRC_DIR/Makefile" ]; then
    BUILD_SYSTEM="makefile"
    CHECK_CMD="make -n check"
    echo "构建系统: Makefile"
elif [ -f "$SRC_DIR/Makefile.in" ]; then
    BUILD_SYSTEM="autotools"
    CHECK_CMD="make -n check"
    echo "构建系统: Autotools (需要先 ./configure)"
else
    echo "构建系统: 未知"
    echo "[warn] 无法自动检测构建系统"
fi
echo ""

# ── 2. 尝试 dry run 测试命令 ──
echo "── [2] 测试命令 dry run ──────────────────"
echo "命令: $CHECK_CMD"
echo ""

if [ "$BUILD_SYSTEM" = "autotools" ] || [ "$BUILD_SYSTEM" = "makefile" ]; then
    # Makefile 项目: make -n check
    if [ -f "$SRC_DIR/Makefile" ]; then
        echo "--- make -n check 输出 (前 50 行) ---"
        (cd "$SRC_DIR" && make -n check 2>&1 | head -50 || true) || echo "[warn] make -n check 失败 (可能需要先 ./configure)"
    else
        echo "[info] 没有 Makefile, 需要先运行 ./configure"
        echo "[info] 请手动执行:"
        echo "  cd $SRC_DIR"
        echo "  ./configure"
        echo "  make -n check"
    fi
elif [ "$BUILD_SYSTEM" = "cmake" ]; then
    echo "--- ctest -N 输出 ---"
    echo "[info] 需要先 cmake + make 构建才能列出测试"
    echo "[info] 请手动执行:"
    echo "  cd $SRC_DIR && mkdir build && cd build"
    echo "  cmake .. && make"
    echo "  ctest -N"
elif [ "$BUILD_SYSTEM" = "meson" ]; then
    echo "--- meson test --list 输出 ---"
    echo "[info] 需要先 meson setup 才能列出测试"
    echo "[info] 请手动执行:"
    echo "  cd $SRC_DIR"
    echo "  meson setup build"
    echo "  cd build && meson test --list"
fi
echo ""

# ── 3. 查找测试文件 ──
echo "── [3] 测试相关文件 ──────────────────────"
echo ""
echo "--- tests/ 目录 ---"
if [ -d "$SRC_DIR/tests" ]; then
    find "$SRC_DIR/tests" -maxdepth 2 -type f \( -name "*.c" -o -name "*.cpp" -o -name "*.sh" -o -name "*.tests" -o -name "*.py" \) 2>/dev/null | head -30 || true
else
    echo "(无 tests/ 目录)"
fi
echo ""

echo "--- test/ 目录 ---"
if [ -d "$SRC_DIR/test" ]; then
    find "$SRC_DIR/test" -maxdepth 2 -type f \( -name "*.c" -o -name "*.cpp" -o -name "*.sh" -o -name "*.py" \) 2>/dev/null | head -30 || true
else
    echo "(无 test/ 目录)"
fi
echo ""

echo "--- 源码目录下的测试文件 (example/test/check) ---"
find "$SRC_DIR" -maxdepth 1 -type f \( -name "example*.c" -o -name "*test*.c" -o -name "*test*.cpp" -o -name "*check*.c" \) 2>/dev/null | head -20 || true
echo ""

# ── 4. 生成 MANIFEST.yml 骨架 ──
echo "── [4] MANIFEST.yml 骨架模板 ─────────────"
echo ""
echo "请将以下内容保存到 test_package/MANIFEST.yml (根据实际情况修改):"
echo ""
echo "----------------------------------------"
cat <<EOF
package: ${PKG_NAME}/${PKG_VER}
homepage: ""

# 上游测试命令
upstream_check_command: "${CHECK_CMD%% *}"

# conanfile.py build() 方法中是否已集成上游测试
upstream_test_in_build: true
upstream_test_command: "make check"

# make check 实际运行的测试程序 (从 [2] 的输出中提取填写)
upstream_tests:
  - file: example.c
    source: $(basename "$SRC_DIR")/example.c
    description: "TODO: 填写测试描述"
    command: "./example"

# test_package 中自带的测试
test_package_tests:
  - file: test.c
    description: "TODO: 填写消费者视角测试描述"
    command: "./test_${PKG_NAME}"

# 测试断言总数 (近似值)
assertion_count: 0
EOF
echo "----------------------------------------"
echo ""

# ── 5. 总结 ──
echo "══════════════════════════════════════════"
echo " 分析完成"
echo "══════════════════════════════════════════"
echo ""
echo "下一步:"
echo "  1. 根据 [2] 的 dry run 输出，确认上游测试列表"
echo "  2. 把测试源文件复制到 test_package/ 目录"
echo "  3. 在 test_package/conanfile.py 的 test() 中编译运行这些测试"
echo "  4. 在 conanfile.py 的 build() 方法末尾加 make check / autotools.make(target='check')"
echo "  5. 填写 test_package/MANIFEST.yml"
echo "  6. 详见 docs/TEST_QUALITY_SPEC.md"
