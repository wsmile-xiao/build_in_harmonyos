# lzbench 2.2 for HarmonyOS

## 概述

lzbench 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。lzbench 是一个压缩算法基准测试工具，支持多种压缩库的性能对比。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | lzbench |
| 版本 | 2.2 |
| 下载地址 | https://github.com/inikep/lzbench/archive/refs/tags/v2.2.tar.gz |
| 官方文档 | https://github.com/inikep/lzbench |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | makefile（直接 Makefile） |

## 编译步骤

```bash
# 1. 下载源码
wget https://github.com/inikep/lzbench/archive/refs/tags/v2.2.tar.gz
tar -xzf lzbench-2.2.tar.gz
cd lzbench-2.2

# 2. 编译（静态链接，禁用 zstd）
make -j$(nproc) BUILD_STATIC=1 DONT_BUILD_ZSTD=1

# 3. 手动安装（Makefile 无 install 目标）
mkdir -p $HOME/usr/local/bin
cp lzbench $HOME/usr/local/bin/
```

## 补丁说明

无需补丁。通过编译选项 `DONT_BUILD_ZSTD=1` 禁用有问题的依赖。

## 遇到的问题

### 问题1: zstd 库依赖 qsort_r 不可用

**现象**: 编译时报 `qsort_r` 函数未定义错误

**原因**: OpenHarmony 不提供 GNU 扩展函数 `qsort_r`

**解决**: 使用 `DONT_BUILD_ZSTD=1` 禁用 zstd 压缩支持

### 问题2: Makefile 无 install 目标

**现象**: `make install` 失败

**原因**: lzbench Makefile 是简单的测试工具构建脚本，无安装目标

**解决**: 手动复制可执行文件到目标目录

## 测试结果

| 测试项 | 结果 |
|--------|------|
| 编译成功 | ✅ |
| 可执行文件可用 | ✅ |
| 基准测试运行 | ⚠️ zstd 禁用，其他算法正常 |
| 完整功能 | ⚠️ partial（缺少 zstd 支持） |

## 验证安装

```bash
# 检查安装
ls -la $HOME/usr/local/bin/lzbench

# 运行基准测试（列出支持的算法）
lzbench -h

# 简单测试
echo "test data" | lzbench -b1
```

## 经验总结

1. lzbench 使用简单 Makefile，无需 configure 步骤
2. `BUILD_STATIC=1` 推荐用于静态链接
3. OpenHarmony 不支持 `qsort_r`，相关依赖需禁用
4. Makefile 无 install 目标，需手动安装

## 参考资料

- https://github.com/inikep/lzbench