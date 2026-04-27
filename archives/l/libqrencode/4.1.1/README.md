# libqrencode 4.1.1 for HarmonyOS

## 概述

libqrencode 是一个快速紧凑的 QR Code 编码库，用于生成 QR 码。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | libqrencode |
| 版本 | 4.1.1 |
| 下载地址 | https://github.com/fukuchi/libqrencode/archive/refs/tags/v4.1.1.tar.gz |
| 官方仓库 | https://github.com/fukuchi/libqrencode |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.12.0 |
| 架构 | aarch64 |
| 编译器 | clang 15.0.4 |
| 构建系统 | CMake |

## 编译步骤

**注意**: autotools 构建在本环境不可用（libtoolize 功能受限），改用 CMake 构建。

```bash
# 1. 下载源码
wget https://github.com/fukuchi/libqrencode/archive/refs/tags/v4.1.1.tar.gz
tar -xzf v4.1.1.tar.gz
cd libqrencode-4.1.1

# 2. CMake 配置
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
         -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_POLICY_VERSION_MINIMUM=3.5

# 3. 编译
make -j$(nproc)

# 4. 安装（staging 模式）
make install DESTDIR=$HOME/tmp/test-install-libqrencode-4.1.1
```

## 补丁说明

无补丁。源码可直接编译。

## 遇到的问题

### 问题1: autotools 构建不可用

**现象**: libtoolize 报错 "func_add_hook: inaccessible or not found"

**原因**: 本环境的 libtoolize 实现不完整

**解决**: 使用 CMake 构建替代 autotools

### 问题2: CMake 版本兼容性

**现象**: CMake 报错 "Compatibility with CMake < 3.5 has been removed"

**原因**: libqrencode 的 CMakeLists.txt 要求 VERSION 3.1.0

**解决**: 添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 参数

## 依赖说明

### 编译依赖

无特殊编译依赖。

### 运行依赖

**qrencode 工具依赖 libpng16.so.16**

打包后的预编译包中 lib/external 目录为空，需要用户先安装 libpng：

```bash
# 方式1: 安装 libpng 预编译包
# 下载 libpng 预编译包并安装

# 方式2: 手动编译 libpng
# 参见 libpng 的编译文档

# 安装后确保 LD_LIBRARY_PATH 包含 libpng 路径
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
qrencode --version
```

## 测试结果

未执行测试（WITH_TESTS=OFF）。编译和安装通过。

## 验证安装

```bash
# 检查库文件
ls -la $HOME/usr/local/lib/libqrencode.a

# 检查头文件
ls -la $HOME/usr/local/include/qrencode.h

# 检查工具（需先安装 libpng）
qrencode --version
# 输出: qrencode version 4.1.1

# 生成 QR 码测试
qrencode -o test.png "Hello QR Code"
```

## 预编译包

| 文件 | 大小 | 说明 |
|------|------|------|
| libqrencode-4.1.1-ohos-aarch64.tar.gz | 250KB | Release 包 |
| libqrencode-4.1.1-ohos-aarch64-debug.tar.gz | - | Debug 符号包 |

**安装命令**:
```bash
sh install-libqrencode-4.1.1.sh
```

**注意事项**: 安装后需确保 libpng16.so.16 可访问。

## 经验总结

1. GitHub tag 源码包缺少 configure 脚本，需使用 autoreconf 或 CMake
2. autotools 在某些环境下可能不可用，CMake 是可靠的替代方案
3. 动态链接工具的外部依赖需在打包时收集或明确标注