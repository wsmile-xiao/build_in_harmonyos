# fast_float

## 软件描述

fast_float 是一个高性能的 C++ header-only 库，提供快速字符串到浮点数/整数的转换功能。它实现了 C++17 标准的 `from_chars` 函数，性能比标准库快 4-5 倍。

## 主要功能

### 核心功能
- **浮点数解析**：支持 `float` 和 `double` 类型的字符串解析
- **整数解析**：支持多种整数类型（int, unsigned, uint64_t 等）和进制（2, 10, 16）
- **精确舍入**：遵循 IEEE 标准，采用"舍入到偶数"规则
- **Locale-independent**：不依赖本地化设置，使用点号作为小数分隔符

### 高级特性
- **C++11 兼容**：最低要求 C++11，支持 C++17/C++20 constexpr 特性
- **UTF-16/UTF-32 支持**：不仅支持 ASCII/UTF-8，还支持 UTF-16 和 UTF-32 输入
- **自定义分隔符**：可通过 `from_chars_advanced` 使用逗号等作为小数分隔符
- **JSON/Fortran 格式**：支持 JSON 和 Fortran 格式的数值解析
- **零内存分配**：不使用 new/malloc，无异常抛出

## 使用场景

### 性能敏感场景
- **大数据处理**：Apache Arrow 使用 fast_float 加速数值解析，性能提升 2-3 倍
- **数据库解析**：DuckDB、ClickHouse 等数据库使用
- **Web 渲染**：Chromium、WebKit 浏览器引擎集成
- **服务器应用**：Redis 使用 fast_float 解析配置和数据

### 标准 C++ 替代方案
- **C++17 from_chars 实现**：GCC 12+ 的标准库已集成 fast_float 算法
- **跨平台兼容**：支持 Visual Studio、macOS、Linux、FreeBSD、鸿蒙
- **嵌入式系统**：无外部依赖，header-only 设计适合嵌入式

### 典型应用示例
```cpp
#include "fast_float/fast_float.h"

// 解析浮点数
double result;
auto answer = fast_float::from_chars(str.data(), str.data() + str.size(), result);

// 解析整数（支持不同进制）
uint64_t i;
fast_float::from_chars(str, str + len, i, 10);  // 十进制
fast_float::from_chars(str, str + len, i, 16);  // 十六进制
fast_float::from_chars(str, str + len, i, 2);   // 二进制
```

## 库类型

**Header-Only INTERFACE Library**

- 无 `.so` 或 `.a` 二进制文件
- 仅包含头文件（`include/fast_float/*.h`）
- 包含 CMake 配置文件（`share/cmake/FastFloat/*.cmake`）
- 使用时只需 `#include "fast_float/fast_float.h"`，无需链接

## 依赖关系

- **无外部依赖**：不依赖任何第三方库
- **构建工具**：CMake >= 3.9
- **编译器要求**：支持 C++11 的编译器
- **平台支持**：32/64 位系统，大/小端架构

## 版本信息

- **最新版本**：7.0.0（2024）
- **许可证**：Apache 2.0 / MIT / BOOST（三重许可）
- **项目地址**：https://github.com/fastfloat/fast_float

## 性能数据

根据官方基准测试（1GB/s 解析速度）：
```
netlib            : 271 MB/s    12.93 Mfloat/s
strtod            : 190 MB/s     9.10 Mfloat/s
abseil            : 430 MB/s    20.52 Mfloat/s
fastfloat         : 1042 MB/s   49.68 Mfloat/s  ⭐
```

fast_float 比标准库快 4-5 倍，比 Abseil 快 2 倍以上。

## 集成方式

### CMake 集成
```cmake
# 方式 1：add_subdirectory
add_subdirectory(fast_float)
target_link_libraries(myapp PUBLIC fast_float)

# 方式 2：FetchContent（CMake 3.11+）
FetchContent_Declare(fast_float
  GIT_REPOSITORY https://github.com/fastfloat/fast_float.git
  GIT_TAG v7.0.0)
FetchContent_MakeAvailable(fast_float)
target_link_libraries(myapp PUBLIC fast_float)

# 方式 3：预编译包（鸿蒙）
target_include_directories(myapp PUBLIC ${CMAKE_INSTALL_PREFIX}/include)
```

### 单头文件集成
可直接下载单头文件版本：
https://github.com/fastfloat/fast_float/releases/download/v7.0.0/fast_float.h

## 鸿蒙适配状态

| 项目 | 状态 | 说明 |
|------|------|------|
| 编译 | ✅ 成功 | clang++ 15.0.4, C++11 |
| 测试 | ✅ 通过 | 功能测试验证 |
| 预编译包 | ✅ 已发布 | fast_float-7.0.0-ohos-aarch64.tar.gz |
| 平台兼容 | ✅ 无问题 | Header-only，无平台特定代码 |

## 相关链接

- [官方仓库](https://github.com/fastfloat/fast_float)
- [性能论文](https://arxiv.org/abs/2101.11408)
- [GCC 集成](https://github.com/llvm/llvm-project/commit/87c016078ad72c46505461e4ff8bfa04819fe7ba)
- [Conan 包](https://conan.io/center/recipes/fast_float)
- [Homebrew 包](https://formulae.brew.sh/formula/fast_float)