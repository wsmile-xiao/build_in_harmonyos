# libdivsufsort

> Lightweight suffix-sorting library

## 基本信息

| 字段 | 值 |
|------|------|
| 软件 | libdivsufsort |
| 许可证 | MIT |
| 语言 | C |
| 构建系统 | CMake |
| 主页 | https://github.com/y-256/libdivsufsort |

## 描述

libdivsufsort 是一个轻量级的后缀排序库，提供高效的后缀数组构建算法。它实现了 divsufsort 算法，可以在 O(n log n) 时间内对任意文本构建后缀数组。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 2.0.1 | built | 2026-06-29 |

## 依赖

无外部依赖。

## 构建参数

- `-DBUILD_SHARED_LIBS=OFF` — 静态链接（R26）
- `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` — CMake 4.x 兼容

## 产物

- `lib/libdivsufsort.a` — 静态库
- `include/divsufsort.h` — 头文件
- `lib/pkgconfig/libdivsufsort.pc` — pkg-config 文件
