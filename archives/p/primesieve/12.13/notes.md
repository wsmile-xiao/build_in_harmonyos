# primesieve 12.13 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-13
- 编译器: clang / clang++
- 状态: built

## 库简介

primesieve 是一个高性能的 C/C++ 质数筛分库，基于优化的埃拉托斯特尼筛法实现。
支持质数生成、质数计数、第 N 个质数计算等功能，内置多线程并行计算和 CPU
指令集优化（x86 AVX512、ARM SVE）。

## 编译步骤

1. **源码下载**: 从 GitHub 下载 primesieve v12.13
   - URL: https://github.com/kimwalisch/primesieve/archive/refs/tags/v12.13.tar.gz
   - SHA256: 4cd3f1b70f6b02d695e6495e6a0fc0fa99b4dc043e0f21686d2cf409e98295c9

2. **CMake 配置**:
   ```bash
   cmake .. \
     -DBUILD_STATIC_LIBS=ON \
     -DBUILD_SHARED_LIBS=OFF \
     -DBUILD_PRIMESIEVE=OFF \
     -DBUILD_TESTS=ON \
     -DBUILD_EXAMPLES=OFF \
     -DBUILD_DOC=OFF \
     -DBUILD_MANPAGE=OFF \
     -DWITH_MULTIARCH=ON \
     -DCMAKE_SYSTEM_NAME=Linux \
     -DCMAKE_SYSTEM_PROCESSOR=aarch64
   ```

3. **编译**:
   ```bash
   cmake --build . -j$(nproc)
   ```
   - 生成静态库 libprimesieve.a

4. **安装**:
   ```bash
   cmake --install .
   ```
   - 库文件: libprimesieve.a
   - 头文件: primesieve.h, primesieve.hpp, primesieve/*.h, primesieve/*.hpp
   - CMake config: primesieveConfig.cmake
   - pkg-config: primesieve.pc

## 构建选项说明

| 选项 | 值 | 说明 |
|------|-----|------|
| BUILD_STATIC_LIBS | ON | 构建静态库 |
| BUILD_SHARED_LIBS | OFF | 禁用共享库 |
| BUILD_PRIMESIEVE | OFF | 禁用命令行工具（仅需库） |
| BUILD_TESTS | ON | 启用上游测试（15 个测试用例，CTest 运行） |
| BUILD_EXAMPLES | OFF | 禁用示例 |
| BUILD_DOC | OFF | 禁用文档 |
| BUILD_MANPAGE | OFF | 禁用 man page 生成 |
| WITH_MULTIARCH | ON | 启用运行时 CPU 指令集分发（ARM SVE） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不识别 OHOS 平台 | E092: CMake 不支持 OHOS | 设置 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64 |
| 2 | 上游测试集成 | 上游 test/ 目录含 15 个测试（count_primes、Riemann_R 等），不依赖 Catch2，为独立 C/C++ 程序 | BUILD_TESTS=ON + cmake.test() 运行 CTest |

## 源码修改

无补丁，源码原样编译。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| pthread | 系统 | 系统库 |

无第三方依赖，仅需系统 pthread。

## 验证结果

### 上游测试（CTest，15 个测试用例）

上游 test/ 目录包含 15 个独立测试程序，不依赖 Catch2，通过 CMake CTest 运行：

| 测试文件 | 测试内容 |
|----------|---------|
| count_primes1.cpp | 统计 10^1 到 10^9 范围内的质数 |
| count_primes2.cpp | 质数计数变体测试 |
| count_primes3.cpp | 质数计数变体测试 |
| count_twins.cpp | 质数孪生对计数 |
| count_triplets.cpp | 质数三元组计数 |
| count_quadruplets.cpp | 质数四元组计数 |
| count_quintuplets.cpp | 质数五元组计数 |
| count_sextuplets.cpp | 质数六元组计数 |
| Riemann_R.cpp | Riemann R 函数近似测试 |
| floorPow2.cpp | floorPow2 数学函数测试 |
| calculator.cpp | 计算器功能测试 |
| clear_primesieve_iterator1.cpp | 迭代器清除测试 (C++) |
| clear_primesieve_iterator2.c | 迭代器清除测试 (C) |
| cpu_info.cpp | CPU 信息检测测试 |
| cpuid.cpp | CPUID 检测测试（aarch64 下空操作） |

### test_package smoke test（4 个消费者测试）

1. iterator 生成前 10 个质数: [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
2. count_primes(0, 10) = 4
3. nth_prime(100) = 541
4. generate_primes(0, 30) 生成 10 个质数

## 交付物

| 文件 | 说明 |
|------|------|
| libprimesieve.a | 静态库（主库） |
| primesieve.pc | pkg-config 文件 |
| primesieveConfig.cmake | CMake 配置文件 |
| primesieve.h / .hpp | C/C++ 头文件 |
| primesieve/*.h / *.hpp | 内部头文件 |

## 注意事项

1. **纯库构建**: 禁用命令行工具 BUILD_PRIMESIEVE=OFF，仅需 libprimesieve.a
2. **ARM SVE 优化**: WITH_MULTIARCH=ON 启用 ARM SVE 运行时分发，适用于 aarch64
3. **无第三方依赖**: primesieve 仅需系统 pthread，无需 Conan 依赖
4. **上游测试**: 上游 test/ 目录含 15 个测试程序，不依赖 Catch2，为独立 C/C++ 程序，通过 BUILD_TESTS=ON + cmake.test() 运行 CTest

---

**最终状态**: built
