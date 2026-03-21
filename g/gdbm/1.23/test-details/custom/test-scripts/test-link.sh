#!/bin/sh
# test-link.sh - 测试 GDBM 库链接和基本功能

LIB_NAME="gdbm"
LIB_DIR="$HOME/usr/local"
TEST_DIR="$(dirname "$0")"

echo "=== Testing $LIB_NAME library ==="
echo "Library path: $LIB_DIR"
echo ""

# 1. 检查库文件是否存在
echo "1. Checking library files..."
if [ -f "$LIB_DIR/lib/lib$LIB_NAME.so" ]; then
    echo "   ✓ Shared library found: lib$LIB_NAME.so"
elif [ -f "$LIB_DIR/lib/lib$LIB_NAME.a" ]; then
    echo "   ✓ Static library found: lib$LIB_NAME.a"
else
    echo "   ✗ Library not found!"
    exit 1
fi

# 检查静态库
if [ -f "$LIB_DIR/lib/lib$LIB_NAME.a" ]; then
    echo "   ✓ Static library found: lib$LIB_NAME.a"
fi

# 2. 检查头文件
echo ""
echo "2. Checking header files..."
if [ -f "$LIB_DIR/include/$LIB_NAME.h" ]; then
    echo "   ✓ Header found: $LIB_NAME.h"
else
    echo "   ✗ Header not found!"
    exit 1
fi

# 检查兼容库头文件
if [ -f "$LIB_DIR/include/dbm.h" ]; then
    echo "   ✓ Compat header found: dbm.h"
fi
if [ -f "$LIB_DIR/include/ndbm.h" ]; then
    echo "   ✓ Compat header found: ndbm.h"
fi

# 3. 编译测试程序
echo ""
echo "3. Compiling test program..."
cd "$TEST_DIR"

CFLAGS="-I$LIB_DIR/include"
LDFLAGS="$LIB_DIR/lib/libgdbm.a"

clang $CFLAGS -o test-gdbm-api test-gdbm-api.c $LDFLAGS
if [ $? -ne 0 ]; then
    echo "   ✗ Compilation failed!"
    exit 1
fi
echo "   ✓ Compilation successful"

# 4. 运行测试
echo ""
echo "4. Running tests..."
./test-gdbm-api
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo ""
    echo "=== All tests passed! ==="
else
    echo ""
    echo "=== Tests failed! ==="
fi

# 清理
rm -f test-gdbm-api

exit $RESULT