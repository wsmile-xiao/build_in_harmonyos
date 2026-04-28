# c-blosc 1.21.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-04-27
- 编译器: clang
- 状态: published

## 编译步骤
```bash
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DBUILD_BENCHMARKS=OFF ..
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 不支持 cmake_minimum_required(VERSION 2.8.12) | 版本兼容性 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 2 | bench.c 编译失败 — CLOCK_MONOTONIC 不可用 | 平台不支持 clock_gettime | 设置 -DBUILD_BENCHMARKS=OFF |
| 3 | CMake 报告 "System is unknown" | 平台未识别 | 使用 generic 实现，功能完整 |

## 源码修改
无补丁。

## 依赖版本
无外部依赖（内置 LZ4 1.9.4, zlib 1.3.1, ZSTD 1.5.6）

## 验证结果
- 1632 测试全部通过 (100%)
- pkg-config --modversion blosc = 1.21.6

## 交付物
- libblosc.so / libblosc.a
- blosc.h, blosc-export.h

## 注意事项
- 硬件加速 shuffle (AVX2/SSE2) 不可用，使用 generic 实现
- 内置压缩算法: blosclz, lz4/lz4hc, zlib, zstd
