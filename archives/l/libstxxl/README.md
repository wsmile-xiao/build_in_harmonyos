# libstxxl

C++ implementation of STL for extra large data sets (STXXL) — 外部存储（out-of-core）STL 实现。

## 软件描述

STXXL 是一个 C++ 标准模板库（STL）的外部存储实现，专为处理超出内存容量的大数据集而设计。它提供了高效的算法和数据结构，支持在磁盘上执行排序、扫描、洗牌等操作，并通过流水线化处理优化 I/O 性能。

核心特性：
- **外部存储容器**: vector、deque、stack、queue、map、priority_queue 等
- **外部存储算法**: sort、ksort、stable_sort、scan、random_shuffle 等
- **流水线化流**: 支持链式流操作，减少 I/O 中间结果
- **多磁盘支持**: 可配置多个磁盘并行 I/O
- **B-tree 和 HashMap**: 支持大规模索引查找

## 许可证

BSL-1.0（Boost Software License 1.0）— 允许商用，无需开源

## 编译版本

| 版本   | 状态   | 编译日期   | 构建系统 | 备注 |
|--------|--------|-----------|---------|------|
| 1.4.1  | built  | 2026-06-10 | cmake   | 静态库，需补丁修复 CMake 版本兼容 |

## OpenHarmony 适配要点

1. **cmake_minimum_required 版本**：源码使用 `VERSION 2.6.2`，不兼容 CMake 4.x；补丁将其改为 `3.5`
2. **CMAKE_SYSTEM_NAME**：需设为 `Linux` 以正确检测 POSIX 系统调用（pthread、mmap、O_DIRECT）
3. **BUILD_SHARED_LIBS=OFF**：建议编译为静态库，避免鸿蒙平台共享库签名/RPATH 问题
4. **磁盘配置**：运行时需创建 `~/.stxxl` 配置文件指定可写磁盘路径（默认 /var/tmp 只读）

## 安装产物

- `lib/libstxxl.a` — 静态库
- `include/stxxl/` — 头文件（algorithm、vector、deque、stream、io 等）

## 使用示例

```cpp
#include <stxxl/vector>
#include <stxxl/sort>

stxxl::vector<int> big_array;  // 外部存储向量
stxxl::sort(big_array.begin(), big_array.end(), MyComparator(), 128 * 1024 * 1024);
```

## 依赖

- pthread（系统自带）
- C++11 编译器