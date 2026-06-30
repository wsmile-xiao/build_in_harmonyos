# isa-l 2.32.0 — README

## 简介

isa-l (Intel Intelligent Storage Acceleration Library) 是 Intel 提供的高性能存储加速算法库，
包含纠删码、压缩、CRC校验等功能的优化实现，支持 x86 和 ARM (NEON/SVE) 架构。

## 本编译版本说明

- **版本**: 2.32.0
- **平台**: OpenHarmony aarch64 (OHOS SDK 26.0.0.18, clang 15.0.4)
- **构建系统**: autotools
- **状态**: built
- **编译日期**: 2026-06-03

### 重要适配说明

1. **SVE优化已禁用**: clang 15.0.4 无法编译 SVE C 内联函数
   (`__attribute__((target("+sve")))+always_inline` 冲突)，NEON优化完整可用
2. **必须传递 `CPPFLAGS="-D__OHOS__"` 给 configure**
3. **igzip 运行时需库在 musl 可搜索的路径中**

## 安装内容

| 文件 | 说明 |
|------|------|
| bin/igzip | 压缩命令行工具 |
| lib/libisal.so.2.0.32 | 共享库 (216导出符号) |
| lib/libisal.so.2 → libisal.so.2.0.32 | 版本符号链接 |
| lib/libisal.so → libisal.so.2.0.32 | 开发符号链接 |
| lib/libisal.a | 静态库 |
| lib/libisal.la | libtool描述文件 |
| lib/pkgconfig/libisal.pc | pkg-config文件 |
| include/isa-l.h | 主头文件 |
| include/isa-l/*.h | 子模块头文件 (9个) |

## 使用方式

### pkg-config 方式

```bash
export PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig
pkg-config --cflags --libs libisal
```

### 静态链接（推荐，避免musl路径问题）

```bash
clang -D__OHOS__ -I$DEFAULT_PREFIX/include \
    $DEFAULT_PREFIX/lib/libisal.a \
    your_program.c -o your_program
```

### 动态链接（需库在系统路径）

```bash
clang -D__OHOS__ -I$DEFAULT_PREFIX/include \
    -L$DEFAULT_PREFIX/lib -lisal \
    your_program.c -o your_program
```

## 补丁列表

1. `0001-erasure_code-aarch64-Makefile.am.patch` — 移除SVE源文件
2. `0002-erasure_code-aarch64-ec_aarch64_dispatcher.c.patch` — SVE函数声明守卫
3. `0003-erasure_code-aarch64-ec_aarch64_highlevel_func.c.patch` — SVE wrapper守卫