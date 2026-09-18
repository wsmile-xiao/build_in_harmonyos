# pdqsort

> Pattern-Defeating Quicksort —— 单头文件、drop-in 替换 `std::sort` 的 C++ 排序库。

## 简介

pdqsort 是 Orson Peters 提出的 pattern-defeating 快排实现：在常见快排会退化的输入
（大量相等元素、已排序、organ-pipe、逆序等）上保持 O(n log n)，同时平均性能与
`std::sort` 相当甚至更好。库只有 `pdqsort.h` 一个文件，提供：

- `pdqsort(begin, end)` / `pdqsort(begin, end, comp)`
- `pdqsort_branchless(begin, end)` / `pdqsort_branchless(begin, end, comp)`
- 内部实现位于 `pdqsort_detail` 命名空间（`pdqsort_internal`/`pdqsort_loop`）

## OHOS 适配要点

- **纯头文件、无依赖**：本仓库不做任何编译（`build()` 为空），`package_type =
  "header-library"`、`no_copy_source = True`、`package_id()` 清空二进制设置，
  只复制 `include/pdqsort.h` 与 `licenses/license.txt`。
- 上游 tarball 没有构建系统与测试（只有头文件 + `bench/` 基准），因此功能验证由
  `test_package` 的 CMake 消费者程序承担：与 `std::sort` 逐元素对照，并覆盖
  pattern-defeating 的退化输入。
- 版本命名：平台版本 `0.0.0-git20180419` 是 Debian 快照 `0.0.0+git20180419` 的
  Conan 形式（`+` 不允许出现在版本里）。
- 头文件按 C++11 及以上条件编译（`#if __cplusplus >= 201103L`），本仓库以 C++17 验证。

## 依赖

无。

## 使用

```cmake
find_package(pdqsort CONFIG REQUIRED)
target_link_libraries(app PRIVATE pdqsort::pdqsort)
```

```cpp
#include <pdqsort.h>
#include <vector>

std::vector<int> v = { 5, 3, 1, 4 };
pdqsort(v.begin(), v.end());            // 等价于 std::sort 的调用形态
pdqsort(v.begin(), v.end(), custom_cmp);
```

## 功能验证

```sh
conan create archives/p/pdqsort/0.0.0-git20180419 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# ctest 1/1；消费者 8/8 断言（与 std::sort 对照）
```
