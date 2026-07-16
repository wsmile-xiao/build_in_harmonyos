# primesieve

primesieve 是一个高性能的 C/C++ 质数筛分库，基于优化的埃拉托斯特尼筛法实现。
支持质数生成、质数计数、第 N 个质数计算等功能，内置多线程并行计算和 CPU
指令集优化（x86 AVX512、ARM SVE）。

## 功能概述
- 质数生成（iterator、generate_primes、generate_n_primes）
- 质数计数（count_primes）
- 第 N 个质数计算（nth_prime）
- 多线程并行筛分
- CPU 指令集运行时分发（x86 POPCNT/AVX512、ARM SVE）

## OHOS 适配
- CMake 构建系统，生成静态库 libprimesieve.a
- 无第三方依赖，仅需系统 pthread
- WITH_MULTIARCH 启用 ARM SVE 运行时分发，适用于 aarch64 平台
- 无需补丁即可在 HarmonyOS 上编译安装

## 依赖关系
- **编译依赖**: 无
- **运行依赖**: pthread（系统库）

## 参考资料
- 官网: https://primesieve.org/
- 源码: https://github.com/kimwalisch/primesieve
