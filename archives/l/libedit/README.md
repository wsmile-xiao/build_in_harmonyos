# libedit for HarmonyOS

## 概述

libedit 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | libedit |
| 版本 | 20240808, 20251016-3.1 |
| 下载地址 | https://thrysoee.dk/editline/ |
| 官方文档 | https://thrysoee.dk/editline/ |

## 鸿蒙环境

| 项目 | 值 |
|------|------|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | autotools |

## 编译步骤

```bash
# 1. 下载源码
wget https://thrysoee.dk/editline/libedit-{version}.tar.gz
tar -xzf libedit-{version}.tar.gz
cd libedit-{version}

# 2. 应用补丁（如有）
patch -p1 < patches/0001-xxx.patch

# 3. 配置
./configure --prefix=$HOME/usr/local {其他选项}

# 4. 编译
make -j$(nproc)

# 5. 安装
make install
```

## 补丁说明

### 0001-chartype-ohos-support.patch

**目的**: 添加 HarmonyOS 系统支持

**修改文件**:
- `chartype.h`: 添加宽字符支持

## 测试结果

详见各版本目录下的 PROGRESS.md

## 验证安装

```bash
# 检查安装
ls -la $HOME/usr/local/lib/libedit*

# 检查功能
ldd $HOME/usr/local/lib/libedit.so
```

## 参考资料

- https://thrysoee.dk/editline/