# lzop 1.04 for HarmonyOS

## 概述

lzop 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。lzop 是一个使用 LZO 算法的快速压缩工具，专注于速度而非压缩率。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | lzop |
| 版本 | 1.04 |
| 下载地址 | https://www.lzop.org/download/lzop-1.04.tar.gz |
| 官方文档 | https://www.lzop.org/ |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | autotools（CMake 替代方案） |

## 编译步骤

```bash
# 1. 下载源码
wget https://www.lzop.org/download/lzop-1.04.tar.gz
tar -xzf lzop-1.04.tar.gz
cd lzop-1.04

# 2. 应用补丁
for patch in patches/*.patch; do
  patch -p1 < "$patch"
done

# 3. 配置（使用 CMake 替代 autotools）
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local

# 4. 编译
make -j$(nproc)

# 5. 安装
make install
```

## 补丁说明

lzop 需要 13 个补丁用于 HarmonyOS 适配：

### autotools 文件更新（0004-0013）
- `0004-autoconf-config.guess~.patch`: 更新 config.guess 模板
- `0005-autoconf-config.sub~.patch`: 更新 config.sub 模板
- `0006-autoconf-install-sh~.patch`: 更新 install-sh 脚本
- `0007-autoconf-compile.patch`: 更新 compile 脚本
- `0008-autoconf-config.guess.patch`: 添加 HarmonyOS 识别
- `0009-autoconf-config.sub.patch`: 添加 ohos 操作系统支持
- `0010-autoconf-depcomp.patch`: 更新 depcomp
- `0011-autoconf-install-sh.patch`: 安装脚本修复
- `0012-autoconf-missing.patch`: missing 脚本修复
- `0013-autoconf-mkinstalldirs.patch`: mkinstalldirs 修复

### CMake 替代方案（0001-0003）
- `0001-CMakeLists.txt.patch`: 添加 CMake 构建支持
- `0002-Makefile.in.patch`: Makefile.in 修复
- `0003-aclocal.m4.patch`: aclocal.m4 宏修复

## 遇到的问题

### 问题1: autotools 在 HMDFS 上有权限问题

**现象**: config.status 执行失败

**原因**: HMDFS 文件系统对临时目录有特殊权限限制

**解决**: 使用 CMake 替代 autotools 进行构建

## 测试结果

| 测试项 | 结果 |
|--------|------|
| 编译成功 | ✅ |
| 基本压缩功能 | ✅ |
| 解压缩功能 | ✅ |
| 完整功能 | ⚠️ partial（CMake 替代方案） |

## 验证安装

```bash
# 检查安装
lzop --version

# 基本压缩测试
echo "test data" > test.txt
lzop test.txt
lzop -d test.txt.lzo
cat test.txt
```

## 经验总结

1. autotools 在 HMDFS 上可能遇到权限问题，可改用 CMake
2. 需要更新完整的 autotools 辅助文件集（config.guess, config.sub, install-sh 等）
3. lzop 依赖 lzo 库进行压缩

## 参考资料

- https://www.lzop.org/
- https://github.com/nicerobot/lzop