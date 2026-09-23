# onednn 3.13 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤
AArch64 OpenMP + TRAINING。真机 ctest 63 二进制 58 pass / 5 fail（pooling 3D segfault、x64 PaddedWeights reorder、eltwise/api 超时）。`CREATE_EXIT:0`；`onednn version=3.13 engine=cpu ok`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `_SC_LEVEL1_*CACHE_SIZE` 未定义 | musl/OHOS 无 glibc cache sysconf | 写死 L1/L2 大小 |
| 2 | R_AARCH64_* 要 -fPIC | OBJECT 库未开 PIC | CMAKE_POSITION_INDEPENDENT_CODE=ON |
| 3 | 默认 X64 | CMAKE_SYSTEM_PROCESSOR 探测失败 | DNNL_TARGET_ARCH=AARCH64 |

## 依赖版本
无
