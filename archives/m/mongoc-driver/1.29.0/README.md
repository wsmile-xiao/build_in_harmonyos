# mongoc-driver 1.29.0 for HarmonyOS

## 概述

MongoDB C 客户端驱动 (mongo-c-driver) 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | mongoc-driver (libmongoc + libbson) |
| 版本 | 1.29.0 |
| 下载地址 | https://github.com/mongodb/mongo-c-driver/releases/download/1.29.0/mongo-c-driver-1.29.0.tar.gz |
| 官方文档 | https://mongoc.org/ |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS/OpenHarmony aarch64 |
| 架构 | aarch64 |
| 编译器 | clang 15.0.4 (LLVM) |
| 构建系统 | CMake + Ninja |

## 编译步骤

```bash
# 1. 下载源码
wget https://github.com/mongodb/mongo-c-driver/releases/download/1.29.0/mongo-c-driver-1.29.0.tar.gz
tar -xzf mongo-c-driver-1.29.0.tar.gz
cd mongo-c-driver-1.29.0

# 2. 设置环境
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
export DEFAULT_PREFIX="$HOME/usr/local"

# 3. CMake 配置（使用 Ninja，只编译静态库）
mkdir -p _build && cd _build
cmake -GNinja \
      -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DCMAKE_SYSTEM_NAME=Linux \
      -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
      -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
      -DCMAKE_C_FLAGS="-fPIC -O2" \
      -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
      -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON \
      -DCMAKE_C_COMPILER_FORCED=ON \
      -DCMAKE_CXX_COMPILER_FORCED=ON \
      -DENABLE_TESTS=OFF \
      -DENABLE_EXAMPLES=OFF \
      -DENABLE_SHARED=OFF \
      -DENABLE_STATIC=ON \
      ..

# 4. 编译
ninja -j$(nproc)

# 5. 安装（DESTDIR 模式用于打包）
DESTDIR=$HOME/tmp/test-install-mongoc-driver-1.29.0 cmake --install .

# 6. 本地安装（验证）
cmake --install .
```

## 关键发现

### CMake 构建系统适配

**问题**: Unix Makefiles 构建系统在 HarmonyOS 上遇到编译器检测失败。

**现象**: CMake 无法检测 clang 编译器，`Check for working C compiler` 失败。

**原因**: CMake 的 TryCompile 机制使用 Make 构建，在 HMDFS 环境下存在兼容性问题。

**解决**: 使用 Ninja 构建系统 + `CMAKE_C_COMPILER_FORCED=ON` 绕过编译器检测。

### RPATH 问题

**问题**: Ninja 生成器不支持 RPATH 更新。

**现象**: `The install of the bson_shared target requires changing an RPATH from the build tree`

**解决**: 只编译静态库 (`ENABLE_SHARED=OFF`)，设置 `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`。

## 依赖关系

| 依赖 | 版本 | 来源 |
|------|------|------|
| OpenSSL | 1.1.1w | 预编译包 |
| zlib | 1.3.1 | 预编译包 |
| zstd | 1.5.7 | 预编译包 |
| snappy | - | 预编译包 |

## 安装产物

```bash
# 静态库
$HOME/usr/local/lib/libbson-static-1.0.a    # BSON 解析库
$HOME/usr/local/lib/libmongoc-static-1.0.a  # MongoDB C 驱动

# pkg-config
pkg-config --modversion libbson-static-1.0 libmongoc-static-1.0
# 1.29.0
# 1.29.0

# 头文件
$HOME/usr/local/include/libbson-1.0/bson/
$HOME/usr/local/include/libmongoc-1.0/mongoc/
```

## 验证安装

```bash
# 检查 pkg-config
pkg-config --libs libmongoc-static-1.0
# -L/home/usr/local/lib -lmongoc-static-1.0 -lresolv -lssl -lcrypto -lsnappy -lzstd -lbson-static-1.0 -pthread

# 简单测试程序
echo '#include <mongoc/mongoc.h>
int main() { mongoc_init(); mongoc_cleanup(); return 0; }' > test.c
clang test.c -o test $(pkg-config --cflags --libs libmongoc-static-1.0)
```

## 状态说明

- **partial**: 编译成功，缺少 make check 测试报告
- **静态库模式**: 无共享库，无需 ELF 签名
- **无补丁**: 使用 CMake 参数适配平台，无需修改源码

## 预编译包

- `mongoc-driver-1.29.0-ohos-aarch64.tar.gz`: 3.6MB
- 包含静态库、头文件、pkg-config 文件、CMake 配置

## 参考资料

- https://mongoc.org/
- https://github.com/mongodb/mongo-c-driver