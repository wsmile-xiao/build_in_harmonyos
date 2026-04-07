#!/bin/sh
# check-env.sh - 鸿蒙编译环境检查脚本
# 用法: source scripts/check-env.sh 或 sh scripts/check-env.sh

echo "=========================================="
echo "  鸿蒙编译环境检查"
echo "=========================================="
echo ""

ERRORS=0
WARNINGS=0

# 必须的环境变量
echo "=== 必要环境变量 ==="

check_var() {
    _cv_var=$1
    _cv_desc=$2
    _cv_required=$3

    _cv_val=$(eval "echo \"\${$_cv_var}\"")
    if [ -n "$_cv_val" ]; then
        echo "✅ $_cv_var=$_cv_val"
    elif [ "$_cv_required" = "required" ]; then
        echo "❌ $_cv_var 未设置 ($_cv_desc)"
        ERRORS=$((ERRORS + 1))
    else
        echo "⚠️  $_cv_var 未设置 ($_cv_desc)"
        WARNINGS=$((WARNINGS + 1))
    fi
}

check_var "TMPDIR" "临时目录" "required"
check_var "CC" "C 编译器" "recommended"
check_var "CXX" "C++ 编译器" "recommended"
check_var "CFLAGS" "C 编译标志" "recommended"
check_var "DEFAULT_PREFIX" "安装前缀" "recommended"
check_var "LD_LIBRARY_PATH" "库路径" "recommended"

echo ""
echo "=== 必要目录 ==="

check_dir() {
    _cd_dir=$1
    _cd_desc=$2

    if [ -d "$_cd_dir" ]; then
        echo "✅ $_cd_desc: $_cd_dir"
    else
        echo "❌ $_cd_desc 不存在: $_cd_dir"
        ERRORS=$((ERRORS + 1))
    fi
}

check_dir "${TMPDIR:-$HOME/tmp}" "临时目录"
check_dir "${DEFAULT_PREFIX:-$HOME/usr/local}/bin" "安装目录 bin"
check_dir "${DEFAULT_PREFIX:-$HOME/usr/local}/lib" "安装目录 lib"

echo ""
echo "=== 编译器 ==="

check_cmd() {
    _cc_cmd=$1
    _cc_desc=$2

    if command -v "$_cc_cmd" >/dev/null 2>&1; then
        _cc_version=$($_cc_cmd --version 2>/dev/null | head -1)
        echo "✅ $_cc_cmd: $_cc_version"
    else
        echo "❌ $_cc_cmd 不存在"
        ERRORS=$((ERRORS + 1))
    fi
}

check_cmd "clang" "Clang 编译器"
check_cmd "cc" "cc 软链"
check_cmd "c++" "c++ 软链"
check_cmd "llvm-ar" "静态库工具"
check_cmd "llvm-ranlib" "库索引工具"

echo ""
echo "=== 构建工具 ==="

check_cmd "make" "Make"
check_cmd "cmake" "CMake"
check_cmd "autoconf" "Autoconf"
check_cmd "automake" "Automake"
check_cmd "pkg-config" "pkg-config"

echo ""
echo "=========================================="

if [ $ERRORS -gt 0 ]; then
    echo "❌ 发现 $ERRORS 个错误，请修复后再编译"
    echo ""
    echo "建议：将以下内容添加到 ~/.zshrc："
    echo ""
    echo "  export TMPDIR=\$HOME/tmp"
    echo "  export DEFAULT_PREFIX=\$HOME/usr/local"
    echo "  export CC=clang"
    echo "  export CXX=clang++"
    echo "  export CFLAGS=\"-fPIC -O2\""
    echo "  export LD_LIBRARY_PATH=\$DEFAULT_PREFIX/lib:\$LD_LIBRARY_PATH"
    echo "  mkdir -p \$TMPDIR \$DEFAULT_PREFIX/{bin,lib,include}"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo "⚠️  发现 $WARNINGS 个警告，建议配置以获得最佳体验"
    exit 0
else
    echo "✅ 环境检查通过，可以开始编译"
    exit 0
fi
