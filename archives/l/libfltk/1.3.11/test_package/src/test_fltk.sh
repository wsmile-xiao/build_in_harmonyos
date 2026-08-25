#!/bin/sh
# test_fltk.sh — fltk 库消费者验证脚本
#
# 验证 fltk 库产物可被真正消费：
#   1) 产物存在性：FL/Fl.H 头文件、libfltk 库、fltk-config 脚本
#   2) 真实编译链接：用 $CC 编译 include FL/Fl.H 并链接 -lfltk 的
#      最小消费者程序（创建 Fl_Window 对象；沙箱无 X display，
#      不 show/run，仅验证编译链接成功）
#
# 用法：test_fltk.sh <pkg_dir> [x11_lib_dir]
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "FAIL: 用法: test_fltk.sh <pkg_dir> [x11_lib_dir]" >&2
    exit 1
fi
PKG="$1"
X11_LIB="${2:-}"

header="$PKG/include/FL/Fl.H"
lib="$(ls "$PKG"/lib/libfltk* 2>/dev/null | head -1 || true)"
config="$PKG/bin/fltk-config"

for f in "$header" "$config"; do
    if [ ! -f "$f" ]; then
        echo "FAIL: 文件缺失: $f"
        exit 1
    fi
done
if [ -z "$lib" ]; then
    echo "FAIL: libfltk 缺失"
    exit 1
fi

# 真实消费者：编译链接一个小程序（创建 Fl_Window，不显示）
# 静态库 libfltk.a 需 C++ 运行时符号（operator new/__cxa_* 等），
# 必须用 C++ 编译器（$CXX）编译链接——CI 中 $CC 可能是 clang
# （C 编译器），不会自动链接 libc++ 导致链接失败
CXX="${CXX:-}"
if [ -z "$CXX" ] || ! command -v "$CXX" >/dev/null 2>&1; then
    for c in clang++ c++ g++; do
        if command -v "$c" >/dev/null 2>&1; then CXX="$c"; break; fi
    done
fi
if [ -z "$CXX" ] || ! command -v "$CXX" >/dev/null 2>&1; then
    echo "SKIP: 无可用 C++ 编译器（\$CXX 未设置且 clang++/c++/g++ 均不存在），仅验证产物存在性"
    exit 0
fi

SRC_DIR=$(mktemp -d)
trap 'rm -rf "$SRC_DIR"' EXIT
cat > "$SRC_DIR/consumer.cxx" <<'EOF'
#include <FL/Fl.H>
#include <FL/Fl_Window.H>
int main(void) {
    /* 沙箱无 X display：仅构造对象验证头文件与库可链接，不 show/run */
    Fl_Window *win = new Fl_Window(100, 100, "consumer");
    delete win;
    return 0;
}
EOF

# fltk-config 提供真实编译/链接参数（头文件与库路径）
CXXFLAGS=$("$config" --cxxflags 2>/dev/null || echo "-I$PKG/include")
LIBS=$("$config" --libs 2>/dev/null || echo "-L$PKG/lib -lfltk_images -lfltk -lX11 -ldl -lm")
# fltk-config --libs 不包含 X11 链接项（静态库 libfltk.a 需显式 -lX11）
if [ -n "$X11_LIB" ]; then
    LIBS="$LIBS -L$X11_LIB -lX11"
fi
# 静态库 libfltk.a 需 C++ 运行时（libc++，OHOS 默认），显式追加
LIBS="$LIBS -lc++ -lc++abi"

if ! "$CXX" $CXXFLAGS "$SRC_DIR/consumer.cxx" $LIBS -o "$SRC_DIR/consumer" 2>"$SRC_DIR/build.log"; then
    echo "FAIL: 消费者程序编译链接失败"
    echo "  CXXFLAGS: $CXXFLAGS" >&2
    echo "  LIBS: $LIBS" >&2
    cat "$SRC_DIR/build.log" >&2
    exit 1
fi
echo "PASS: 消费者程序编译链接成功（include FL/Fl.H + -lfltk）"

echo "PASS: fltk 可被真实消费（头文件/库/fltk-config/编译链接）"
exit 0
