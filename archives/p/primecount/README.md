# primecount

## 简介

primecount 是 Kim Walisch 开发的高性能素数计数库，用于计算不超过 x 的素数个数 π(x)，实现了 Xavier Gourdon 等组合型素数计数算法，复杂度可达 O(x^(2/3) / log²x)。同时提供 `primecount` 命令行工具。

## 功能概述

- **C/C++ API**：`primecount_pi(x)`、`primecount_nth_prime(n)`、`primecount_phi(x,a)` 等，含 128 位接口
- **算法**：Gourdon / Deleglise-Rivat / Legendre / Meissel 等组合型算法
- **命令行工具**：`primecount` 可直接在终端计算 π(x)、第 n 个素数等
- **多线程**：可选 OpenMP 并行（本适配已禁用）

## OHOS 适配

### 适配要点

1. **零外部依赖**：源码自带 vendored `lib/primesieve`，默认 `BUILD_LIBPRIMESIEVE=ON` 从源码构建，无需 Conan 依赖
2. **静态库**：构建静态库 `libprimecount.a`（上游默认 `BUILD_STATIC_LIBS=ON`），避免 .so 污染系统目录
3. **禁用 OpenMP**：`WITH_OPENMP=OFF`，OHOS 可能不附带 libomp，禁用后退化为串行实现，功能完整
4. **禁用 Multiarch**：`WITH_MULTIARCH=OFF`，关闭运行期 SVE/AVX512 CPU 分发，使用基础 aarch64 代码路径
5. **无平台补丁**：纯计算库，不涉及图形/HAL/系统底层接口，无需适配补丁

### 混合类型

primecount 既有静态库 `libprimecount` 又有可执行文件 `primecount`，按 R38 在软件级目录提供 `commands.json`。

## 功能验证

```bash
# Conan 构建
conan create archives/p/primecount/8.5/ --build=missing

# test_package 输出
# primecount 8.5: pi(100)=25 pi(1000)=168 nth_prime(1)=2 OK

# 命令行 smoke test
primecount 100
# 25
```

## 依赖

- 无外部 Conan 依赖（libprimesieve 已 vendored）

## 参考

- 官方仓库：https://github.com/kimwalisch/primecount
