# DRAFT-libfork-3.6.0-libcxx-missing-headers：OHOS 定制 libc++ 缺失 <source_location> 与 ranges 算法不完整的兼容修复

> Contributor: tianyi_wang | Status: Draft | Updated: 2026-09-03
> Source: libfork 3.6.0 全量适配（OHOS clang 15, aarch64-unknown-linux-ohos）

## 背景

libfork 3.6.0 是 header-only C++23 协程 fork-join 库（CMake，INTERFACE 目标
libfork::libfork，`target_compile_features cxx_std_23`）。在 HarmonyOS PC 工具链
（ohos-sdk_26.0.0.18 native llvm，clang 15.0.4，`-std=c++2b`）上编译上游单头文件
自检与消费者测试时，连续暴露两类**工具链缺口**，而非 libfork 自身缺陷：

1. `#include <source_location>` → fatal error: 'source_location' file not found
2. 一批 `std::ranges::` 算法（shuffle / max_element / destroy /
   uninitialized_default_construct_n / empty）报 "no member named ... in namespace 'std::ranges'"

## 错误 1：<source_location> 头文件缺失

### 现象

```text
fatal error: 'source_location' file not found
#include <source_location> // for source_location
```

### 根因

OHOS 定制 libc++（`libcxx-ohos/include/c++/v1`，`_LIBCPP_VERSION 15004`）不提供
`<source_location>` 头文件；`version` 头中 `__cpp_lib_source_location`（201907L）与
`__cpp_lib_syncbuf`（201803L）的宏定义被注释禁用（表格声明存在但实际不定义）。
因此上游无条件 `#include <source_location>` 的代码必然失败，且没有可用的
feature-test 宏来探测（因为宏也未定义）。

### 修复

在 `utility.hpp` 中做双重能力探测并回退（无平台宏，纯能力探测）：

```cpp
#if defined(__cpp_lib_source_location) && __has_include(<source_location>)
#include <source_location> // for source_location
#endif
```

并在库内部命名空间提供最小占位类型（默认参数语义保留，`non_null()` 的
NDEBUG 断言分支因此不受影响）：

```cpp
struct source_location_t {
  constexpr auto current() const noexcept -> source_location_t { return *this; }
  constexpr auto file_name() const noexcept -> const char * { return ""; }
  constexpr auto line() const noexcept -> int { return 0; }
  constexpr auto function_name() const noexcept -> const char * { return ""; }
};
```

## 错误 2：std::ranges 算法集不完整（incomplete ranges 被禁用）

### 现象

```text
error: no member named 'shuffle' in namespace 'std::ranges'; did you mean 'std::shuffle'?
error: no member named 'max_element' in namespace 'std::ranges'
error: no type named 'destroy' in namespace 'std::ranges'
error: no member named 'uninitialized_default_construct_n' in namespace 'std::ranges'
error: no member named 'empty' in namespace 'std::ranges'
```

### 根因

`ranges_shuffle.h` / `ranges_max_element.h` 等头文件**存在**，但整体包裹在
`#if _LIBCPP_STD_VER > 17 && !defined(_LIBCPP_HAS_NO_INCOMPLETE_RANGES)` 中——
OHOS 定制版定义了 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`，使 libc++ 15 中标记为
"incomplete" 的 ranges 算法（shuffle/max_element/destroy/uninitialized_*
/empty/fold 等）符号全部未导出。`std::ranges::begin/end/size/iterator_t/for_each`
等核心设施不受影响（libfork 大量使用它们，编译通过）。

### 修复

逐一替换为语义等价的经典算法（保留行为，不引入平台宏）：

| 原写法 | 替换 |
|---|---|
| `std::ranges::empty(r)` | `std::ranges::size(r) == 0` |
| `std::ranges::destroy(span)` | `std::destroy(span.begin(), span.end())` |
| `std::ranges::uninitialized_default_construct_n(p,n)` | `std::uninitialized_default_construct_n(p,n)` |
| `std::ranges::shuffle(c, rng)` | `std::shuffle(c.begin(), c.end(), rng)` |
| `std::ranges::max_element(r, {}, proj)` | `std::max_element(b, e, [](a,b){ return proj(a) < proj(b); })` |

## 验证

```bash
# 探针：经典替代 + ranges::size 在 OHOS libc++ 可用
clang++ -std=c++2b -O2 /tmp/probe.cpp && ./probe          # exit 0
# 上游等价自检（fib(10)==55）+ fold/for_each 覆盖（含被补丁路径）
clang++ -std=c++2b -O2 -pthread -I include ... -o fib_check && ./fib_check   # exit 0
clang++ -std=c++2b -O2 -pthread -I include ... -o fold_check && ./fold_check # exit 0
# 配方门禁
conan-verify libfork 3.6.0   # G0-G4 + L2/L4/L5 全 PASS
finish libfork 3.6.0 built   # W3 本地 CI 模拟（build_and_test.sh）通过
```

## 适用边界

- 适用：任何在 HarmonyOS PC（OHOS SDK 26.x，clang 15，libcxx-ohos）上适配
  使用 `<source_location>` 或 std::ranges 算法集的 C++20/23 库；修复方式为
  能力探测回退 + 经典算法替代，对上游行为零改动。
- 反例/限制：若库使用大量 ranges 视图/管道（views 层未被禁用，但需逐一确认），
  或依赖 ranges 算法性能特性，替换为经典算法可能带来细微行为/性能差异；
  依赖 std::format 的库不受影响（<format> 头存在）。
- 与 E130 的区别：E130 描述 libcxx-ohos 需要 C++17 最低标准；本条描述
  C++20/23 设施的**缺失**（source_location 头 + incomplete ranges 禁用），
  属于同一 libcxx-ohos 上的互补缺口，非等价命中。
