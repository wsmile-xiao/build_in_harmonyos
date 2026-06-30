#!/bin/bash
# post-download hook for libplacebo
# 自动补充 git submodule: fast_float
#
# 背景问题: libplacebo 使用 git submodules 管理 3rdparty 依赖，
# 但 tar.gz 发布包不包含 submodule 内容，导致 G0 干净构建验证失败。
# 此脚本在 tarball 解压后、构建前自动补充缺失的 fast_float 头文件。

set -e

FAST_FLOAT_VER="6.1.6"

# 确定 fast_float 目录位置
# 通常在 3rdparty/fast_float/ 下
FAST_FLOAT_DIR="$BUILD_SRC_DIR/3rdparty/fast_float"

# 如果 BUILD_SRC_DIR 未设置，尝试从当前目录推断
if [ -z "$BUILD_SRC_DIR" ]; then
    # 检查当前目录是否是 libplacebo 源码目录
    if [ -f "meson.build" ] && [ -d "3rdparty" ]; then
        FAST_FLOAT_DIR="3rdparty/fast_float"
    else
        echo "ERROR: BUILD_SRC_DIR 未设置，且当前目录不是 libplacebo 源码目录"
        exit 1
    fi
fi

# 检查 fast_float 目录是否存在
if [ ! -d "$FAST_FLOAT_DIR" ]; then
    echo "ERROR: fast_float 目录不存在: $FAST_FLOAT_DIR"
    exit 1
fi

# 检查是否已经有 fast_float 头文件
if [ -d "$FAST_FLOAT_DIR/include/fast_float" ] && [ "$(ls -A $FAST_FLOAT_DIR/include/fast_float/*.h 2>/dev/null)" ]; then
    echo "fast_float headers already present, skipping"
    exit 0
fi

echo "补充 fast_float 头文件..."
mkdir -p "$FAST_FLOAT_DIR/include/fast_float"

# 优先使用本地已有文件（避免网络下载）
# 方案1: 从预下载的 tarball 复制
LOCAL_TARBALL="/storage/Users/currentUser/tmp/fast_float-v6.1.6.tar.gz"
if [ -f "$LOCAL_TARBALL" ]; then
    echo "使用本地 tarball: $LOCAL_TARBALL"
    tar xzf "$LOCAL_TARBALL" \
        --strip-components=3 \
        -C "$FAST_FLOAT_DIR/include/fast_float" \
        "fast_float-${FAST_FLOAT_VER}/include/fast_float"
    echo "✅ fast_float submodule supplemented from local tarball"
    exit 0
fi

# 方案2: 从已有编译目录复制
EXISTING_HEADERS="/storage/Users/currentUser/builds/libplacebo-7.349.0.work/3rdparty/fast_float/include/fast_float"
if [ -d "$EXISTING_HEADERS" ]; then
    echo "从已有编译目录复制: $EXISTING_HEADERS"
    cp -r "$EXISTING_HEADERS"/* "$FAST_FLOAT_DIR/include/fast_float/"
    echo "✅ fast_float submodule copied from existing build"
    exit 0
fi

# 方案3: 从 GitHub 下载（最后的备选）
FAST_FLOAT_URL="https://github.com/fastfloat/fast_float/archive/refs/tags/v${FAST_FLOAT_VER}.tar.gz"
echo "Downloading fast_float v${FAST_FLOAT_VER} from GitHub..."
curl -L "$FAST_FLOAT_URL" -o "$FAST_FLOAT_DIR/fast_float.tar.gz"

echo "Extracting fast_float headers..."
tar xzf "$FAST_FLOAT_DIR/fast_float.tar.gz" \
    --strip-components=3 \
    -C "$FAST_FLOAT_DIR/include/fast_float" \
    "fast_float-${FAST_FLOAT_VER}/include/fast_float"

# 清理临时文件
rm -f "$FAST_FLOAT_DIR/fast_float.tar.gz"

echo "✅ fast_float submodule supplemented successfully"
echo "   Headers installed to: $FAST_FLOAT_DIR/include/fast_float/"