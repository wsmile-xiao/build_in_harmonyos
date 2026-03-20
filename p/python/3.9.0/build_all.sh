#!/bin/bash
# Python 3.9.0 鸿蒙系统完整构建脚本
# 用法: ./build_all.sh

set -e

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
WORK_DIR=~/python/Python-3.9.0-work
PATCH_DIR=$SCRIPT_DIR/patches

echo "=============================================="
echo "Python 3.9.0 鸿蒙系统构建脚本"
echo "=============================================="
echo ""

# 检查源码目录
if [ ! -d "$WORK_DIR" ]; then
    echo "错误: 工作目录不存在: $WORK_DIR"
    echo "请先解压源码: cp -r ~/python/Python-3.9.0 ~/python/Python-3.9.0-work"
    exit 1
fi

cd "$WORK_DIR"
export LD_LIBRARY_PATH=.

# ============================================
# 步骤 1: 应用补丁
# ============================================
echo ""
echo "[步骤 1/6] 应用补丁..."
echo ""

for patch_file in "$PATCH_DIR"/*.patch; do
    if [ -f "$patch_file" ]; then
        patch_name=$(basename "$patch_file")
        echo -n "  应用 $patch_name... "
        if patch -p1 --dry-run < "$patch_file" >/dev/null 2>&1; then
            patch -p1 < "$patch_file" >/dev/null 2>&1
            echo "✓"
        else
            echo "已应用或跳过"
        fi
    fi
done

# ============================================
# 步骤 2: Configure
# ============================================
echo ""
echo "[步骤 2/6] 运行 configure..."
echo ""

if [ ! -f Makefile ]; then
    ./configure --prefix=$HOME/usr/local --enable-shared 2>&1 | tail -5
else
    echo "  Makefile 已存在，跳过 configure"
fi

# ============================================
# 步骤 3: 修改 Makefile（关键）
# ============================================
echo ""
echo "[步骤 3/6] 修改 Makefile..."
echo ""

# BLDSHARED 用于构建 libpython.so，不应包含 -lpython
echo "  设置 BLDSHARED（构建 libpython.so）..."
sed -i 's|^BLDSHARED=.*|BLDSHARED=\t$(CC) -shared $(PY_CORE_LDFLAGS)|' Makefile

# LDSHARED 用于构建扩展模块，必须包含 -lpython
echo "  设置 LDSHARED（构建扩展模块）..."
sed -i 's|^LDSHARED=.*|LDSHARED=\t$(CC) -shared $(PY_LDFLAGS) -L. -lpython$(LDVERSION)|' Makefile

echo "  ✓ Makefile 已修改"

# ============================================
# 步骤 4: 修改 pyconfig.h
# ============================================
echo ""
echo "[步骤 4/6] 修改 pyconfig.h..."
echo ""

# 禁用 CAN socket 宏
sed -i 's/^#define HAVE_LINUX_CAN_RAW_FD_FRAMES 1/\/\* #undef HAVE_LINUX_CAN_RAW_FD_FRAMES \*\//' pyconfig.h 2>/dev/null || true
sed -i 's/^#define HAVE_LINUX_CAN_RAW_JOIN_FILTERS 1/\/\* #undef HAVE_LINUX_CAN_RAW_JOIN_FILTERS \*\//' pyconfig.h 2>/dev/null || true
echo "  ✓ CAN socket 宏已禁用"

# ============================================
# 步骤 5: 构建 Python 核心和解释器
# ============================================
echo ""
echo "[步骤 5/6] 构建 Python 核心和解释器..."
echo ""

make 2>&1 | tail -10

if [ -f python3.9 ] && [ -f libpython3.9.so ]; then
    echo "  ✓ Python 核心构建成功"
else
    echo "  ✗ Python 核心构建失败"
    exit 1
fi

# ============================================
# 步骤 6: 构建扩展模块
# ============================================
echo ""
echo "[步骤 6/6] 构建扩展模块..."
echo ""

mkdir -p build

# 构建函数
build() {
    local name=$1
    local src=$2
    local cflags="${3:-}"
    local objs="${4:-}"
    local libs="${5:-}"
    
    clang -fPIC -Wno-unused-result -DNDEBUG -g -fwrapv -O3 -Wall -std=c99 \
          -I./Include/internal -I./Include -I. $cflags -c "$src" -o build/${name}.o 2>/dev/null
    clang -shared -L. -lpython3.9 build/${name}.o $objs -o ${name}.so $libs 2>/dev/null
}

CORE_MOD="-DPy_BUILD_CORE_MODULE"

# 核心模块
echo "  构建核心模块..."
build _struct Modules/_struct.c
build array Modules/arraymodule.c
build _datetime Modules/_datetimemodule.c
build _random Modules/_randommodule.c "$CORE_MOD"
build _bisect Modules/_bisectmodule.c
build _heapq Modules/_heapqmodule.c
build _pickle Modules/_pickle.c "$CORE_MOD"
build _json Modules/_json.c "$CORE_MOD"
build _csv Modules/_csv.c
build _opcode Modules/_opcode.c
build _queue Modules/_queuemodule.c
build _statistics Modules/_statisticsmodule.c
build _contextvars Modules/_contextvarsmodule.c
build _zoneinfo Modules/_zoneinfo.c
build _asyncio Modules/_asynciomodule.c "$CORE_MOD"

# 系统模块
echo "  构建系统模块..."
build fcntl Modules/fcntlmodule.c
build grp Modules/grpmodule.c
build select Modules/selectmodule.c
build mmap Modules/mmapmodule.c
build syslog Modules/syslogmodule.c
build _posixsubprocess Modules/_posixsubprocess.c
build audioop Modules/audioop.c
build _socket Modules/socketmodule.c

# unicodedata
build unicodedata Modules/unicodedata.c

# math/cmath
echo "  构建 math/cmath..."
clang -fPIC -I./Include -I. -c Modules/_math.c -o build/_math.o 2>/dev/null
build math Modules/mathmodule.c "$CORE_MOD" build/_math.o -lm
build cmath Modules/cmathmodule.c "$CORE_MOD" build/_math.o -lm

# 编码模块
echo "  构建编码模块..."
build _multibytecodec Modules/cjkcodecs/multibytecodec.c
for codec in cn jp kr tw hk iso2022; do
    build _codecs_$codec Modules/cjkcodecs/_codecs_$codec.c
done

# expat/XML
echo "  构建 XML 模块..."
EXPAT_FLAGS="-DHAVE_EXPAT_CONFIG_H=1 -DXML_POOR_ENTROPY=1 -I./Modules/expat"
for f in xmlparse xmlrole xmltok xmltok_impl xmltok_ns; do
    clang -fPIC $EXPAT_FLAGS -I./Include -c Modules/expat/$f.c -o build/$f.o 2>/dev/null
done
EXPAT_OBJS="build/xmlparse.o build/xmlrole.o build/xmltok.o build/xmltok_impl.o build/xmltok_ns.o"
build pyexpat Modules/pyexpat.c "$EXPAT_FLAGS -I./Include/internal" "$EXPAT_OBJS"
build _elementtree Modules/_elementtree.c "$EXPAT_FLAGS -I./Include/internal" "$EXPAT_OBJS"

# 哈希模块
echo "  构建哈希模块..."
for mod in md5 sha1 sha256 sha512; do
    build _$mod Modules/${mod}module.c "$CORE_MOD"
done
build _sha3 Modules/_sha3/sha3module.c "$CORE_MOD"

# _blake2
clang -fPIC $CORE_MOD -I./Include/internal -I./Include -I. \
      -c Modules/_blake2/blake2b_impl.c -o build/blake2b.o 2>/dev/null
clang -fPIC $CORE_MOD -I./Include/internal -I./Include -I. \
      -c Modules/_blake2/blake2s_impl.c -o build/blake2s.o 2>/dev/null
clang -fPIC $CORE_MOD -I./Include/internal -I./Include -I. \
      -c Modules/_blake2/blake2module.c -o build/blake2module.o 2>/dev/null
clang -shared -L. -lpython3.9 build/blake2b.o build/blake2s.o build/blake2module.o -o _blake2.so 2>/dev/null

# ============================================
# 完成
# ============================================
echo ""
echo "=============================================="
echo "构建完成！"
echo "=============================================="
echo ""

# 统计
EXT_COUNT=$(ls *.so 2>/dev/null | grep -v libpython | wc -l)
echo "生成文件:"
echo "  - python3.9 (解释器)"
echo "  - libpython3.9.so (共享库)"
echo "  - $EXT_COUNT 个扩展模块"
echo ""

# 验证
echo "验证..."
./python3.9 -c "
import sys
print('  Python', sys.version.split()[0])
print('  Platform:', sys.platform)
" 2>/dev/null

echo ""
echo "运行测试: export LD_LIBRARY_PATH=. && ./python3.9 -c 'import socket, hashlib, json'"