# primesieve — 快速质数生成器

## 简介

primesieve 是一个高性能的 C/C++ 质数生成库和命令行工具，基于筛法算法（埃拉托斯特尼筛法的优化变种）实现。它支持生成质数、计数质数、计算第 n 个质数等操作，并能自动利用多核 CPU 进行并行计算。

- **项目主页**: https://github.com/kimwalisch/primesieve
- **许可证**: BSD-2-Clause
- **语言**: C++ (提供 C 和 C++ API)
- **构建系统**: CMake

## 功能特性

- 生成质数：支持迭代器逐个生成质数，或批量生成质数列表
- 计数质数：快速计算任意区间内的质数数量
- 第 n 个质数：计算第 n 个质数的值
- 质数孪生/三连/四连/五连/六连计数
- 多线程并行计算：自动检测 CPU 核心数并利用多线程加速
- C 和 C++ 双重 API：提供 `primesieve.h`（C API）和 `primesieve.hpp`（C++ API）
- 命令行工具：`primesieve` 可直接在终端使用

## 编译信息

| 项目 | 值 |
|------|-----|
| 当前版本 | 12.13 |
| 构建系统 | cmake |
| 编译器 | clang 15.0.4 |
| 目标平台 | OpenHarmony / HarmonyOS (aarch64) |
| 安装前缀 | ~/usr/local |
| 编译依赖 | 无 |
| 状态 | ✅ published |

### 编译选项

```bash
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_TESTS=ON ..
make -j2
make install DESTDIR=$TEST_PREFIX
```

### 测试结果

- CTest 测试套件：34 个测试全部通过
- 总耗时：20.43 秒
- 无跳过或超时

## 安装产物

预编译包包含以下文件：

| 类别 | 文件 |
|------|------|
| 可执行文件 | `bin/primesieve` |
| 动态库 | `lib/libprimesieve.so` |
| 静态库 | `lib/libprimesieve.a` |
| C 头文件 | `include/primesieve.h`, `include/primesieve/iterator.h` |
| C++ 头文件 | `include/primesieve.hpp`, `include/primesieve/iterator.hpp`, `include/primesieve/StorePrimes.hpp`, `include/primesieve/primesieve_error.hpp` |
| CMake 配置 | `lib/cmake/primesieve/` |
| pkg-config | `lib/pkgconfig/primesieve.pc` |
| Man 页面 | `share/man/man1/primesieve.1` |

## 使用示例

### 命令行

```bash
# 计算小于 1000 的质数数量
primesieve 1000
# 输出: Primes: 168

# 查看版本
primesieve --version

# 计算第 100 个质数
primesieve -n 100

# 计数质数孪生
primesieve 1000 --count-twins
```

### C API

```c
#include <primesieve.h>
#include <stdio.h>

int main() {
    uint64_t count = primesieve_count_primes(0, 1000);
    printf("质数数量: %llu\n", count);  // 输出: 168
    return 0;
}
```

### C++ API

```cpp
#include <primesieve.hpp>
#include <iostream>

int main() {
    primesieve::iterator it;
    uint64_t prime = it.next_prime();
    while (prime < 100) {
        std::cout << prime << " ";
        prime = it.next_prime();
    }
    return 0;
}
```

## 版本历史

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 12.13 | ✅ published | 2026-06-01 |