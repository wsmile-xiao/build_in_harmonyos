# greg7mdp-gtl

## 是什么

`gtl`（Greg's Template Library）是 Gregory Popovitch 维护的 **header-only C++ 容器库**，
前身是广为人知的 `parallel-hashmap`。它在标准库容器之上提供：

- **并行（分片）哈希容器**：`gtl::parallel_flat_hash_map/set`、`gtl::parallel_node_hash_map/set`（可配 N 个分片与锁类型）
- **开放寻址哈希容器**：`gtl::flat_hash_map/set`、`gtl::node_hash_map/set`（abseil-cpp `raw_hash_set` 系的独立移植）
- **有序容器**：`gtl::btree_map/set/multimap/multiset`
- **工具容器与辅助件**：`gtl::bit_vector`、`gtl::lru_cache` / `mt_lru_cache`、`gtl::vector`（小字符串/小向量优化）、`gtl::stopwatch`、`gtl::memoize`、`gtl::soa`、`gtl::phmap_dump`（序列化/落盘）

交付物只有头文件，无任何链接产物。

## 功能概述

- O(1) 均摊查找的哈希 map/set，支持 `dump/load` 落盘序列化
- 分片并行容器：默认 `std::shared_mutex`，也提供 `std::mutex`（`*_m` 别名）与 `NullMutex`（`*_d`）变体
- `btree_*`：节点型有序容器，迭代器按 key 升序，内存局部性优于红黑树
- `bit_vector`：位压缩存储，支持 `set/reset/flip/test/count`
- 跨平台：同一份头文件在 x86_64 走 SSE2/SSSE3 快路径，其余架构走可移植实现

## OHOS 适配要点

- **有 x86 SSE 快路径**：`include/gtl/gtl_config.hpp` 中 `#include <emmintrin.h>` / `#include <tmmintrin.h>` 都在 `#if GTL_HAVE_SSE2` / `#if GTL_HAVE_SSSE3` **条件块内**；这两个宏由 `__SSE2__` / `__SSSE3__` 预处理宏推导，**aarch64 下恒为 0**，`phmap.hpp` 的 `Group` 退化为 `GroupPortableImpl` 可移植实现。设备编译探针实测输出 `GTL_HAVE_SSE2=0 GTL_HAVE_SSSE3=0`，构建面不引用任何 x86 内建函数。
- **无 glibc printf 钩子**：`register_printf_*` / `printf.h` 全仓 0 命中。
- **零补丁**：源码树与发布 tarball 逐字节一致；上游测试树的 googletest 获取改由 conan 提供。
- `CMAKE_CXX_STANDARD` 上游默认 20；设备 clang 15 / libc++ 两档实测均可通过全部 2207 个上游用例：原生轮按上游默认 **C++20**，conan 轮因 profile `compiler.cppstd=17` 经 `conan_toolchain.cmake` 注入而实际按 **C++17** 构建（gtest 1.17 要求 ≥C++17，已满足；`test_package` 显式钉回 20）。

## 依赖关系

- 编译期依赖：无（纯标准库 + 自带头文件），`conan` 侧 `requires = []`
- 测试期依赖：`gtest/1.17.0.2`（`test_requires`，不进交付依赖链）
- 运行期依赖：无

## 参考资料

- 源码仓库：https://github.com/greg7mdp/gtl
- 上游文档：https://greg7mdp.github.io/gtl/
- ConanCenterIndex 配方：https://github.com/conan-io/conan-center-index/tree/master/recipes/greg7mdp-gtl
