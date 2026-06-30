# isl26

Integer Set Library (ISL) 是一个用于操作整数集合和多面体（polyhedra）的库，主要用于编译器优化和代码生成。

## 概述

isl 是一个旨在用于编译器后端（如 GCC、LLVM）的整数集合和多面体操作库。它提供了以下功能：

- 整数集合操作
- 多面体操作
- 依赖分析
- 代码生成

## 编译状态

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.26 | built | 2026-05-29 |

## 编译说明

### 依赖

- **gmp**: GNU Multiple Precision Arithmetic Library（必需）

### 编译参数

```bash
./configure --prefix=$DEFAULT_PREFIX --disable-shared --enable-static \
  CPPFLAGS="-I$DEFAULT_PREFIX/gmp-6.3.0-ohos-aarch64/include" \
  LDFLAGS="-L$DEFAULT_PREFIX/gmp-6.3.0-ohos-aarch64/lib"
```

### 平台适配要点

1. **config.guess**: 需要添加 HarmonyOS 平台识别逻辑
2. **ffs函数**: 需要使用 `__builtin_ffs` 替代 `ffs`（musl libc 不提供 ffs）
3. **umask**: configure 脚本中的 `umask 077` 需改为 `umask 022`（HMDFS 权限问题）

## 补丁列表

- `0001-config.guess-harmonyos.patch` - HarmonyOS 平台识别
- `0002-ffs-builtin.patch` - ffs 函数检查修改
- `0003-use-builtin-ffs.patch` - 源码使用 builtin_ffs

## 使用

```bash
# pkg-config
pkg-config --cflags isl
pkg-config --libs isl

# 链接静态库
-lisl -lgmp
```

## 来源

- 官方网站: https://libisl.org/
- 源码: https://github.com/Meinersbur/isl