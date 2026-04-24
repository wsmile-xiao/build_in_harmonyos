# lzlib 1.15 for HarmonyOS

## 概述

lzlib 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。lzlib 是一个数据压缩库，提供在内存中进行 LZMA 压缩的功能。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | lzlib |
| 版本 | 1.15 |
| 下载地址 | https://download.savannah.gnu.org/releases/lzip/lzlib/lzlib-1.15.tar.gz |
| 官方文档 | https://www.nongnu.org/lzip/lzlib/manual/lzlib.html |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | custom_configure（作者自定义脚本） |

## 编译步骤

```bash
# 1. 下载源码
wget https://download.savannah.gnu.org/releases/lzip/lzlib/lzlib-1.15.tar.gz
tar -xzf lzlib-1.15.tar.gz
cd lzlib-1.15

# 2. 配置（使用作者自定义 configure 脚本）
./configure --prefix=$HOME/usr/local

# 3. 编译
make -j$(nproc)

# 4. 安装
make install
```

## 补丁说明

无需补丁。lzlib 使用作者 Antonio Diaz Diaz 自定义的 configure 脚本，该脚本已支持标准 Linux 环境，在 HarmonyOS 上可直接编译。

## 遇到的问题

无重大问题。编译过程顺利，静态库 liblz.a 可正常使用。

## 测试结果

| 测试项 | 结果 |
|--------|------|
| 静态库编译 | ✅ |
| 测试套件 | ✅ 通过 |
| 功能验证 | ✅ |

## 验证安装

```bash
# 检查安装
ls -la $HOME/usr/local/lib/liblz.a

# 检查头文件
ls -la $HOME/usr/local/include/lzlib.h
```

## 经验总结

1. lzlib 使用自定义 configure 薄壳脚本，非标准 autotools
2. 仅生成静态库（liblz.a），不生成共享库
3. plzip 依赖此库进行 LZMA 压缩

## 参考资料

- https://www.nongnu.org/lzip/lzlib.html
- https://download.savannah.gnu.org/releases/lzip/lzlib/