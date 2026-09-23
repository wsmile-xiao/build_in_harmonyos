# DRAFT: clang 15+ 弃用 `__has_trivial_copy`（clang 定义 `__GNUC__=4` 误入 g++<5 分支）

- **草稿 ID**: DRAFT-robin-hood-hashing-3.11.5-clang15-has-trivial-copy-deprecated
- **来源库**: robin-hood-hashing 3.11.5（OHOS arm64, clang 15.0.4, OHOS SDK 26.0.0.18）
- **状态**: 草稿（待主编 promote 为正式 E 条目）

## 问题

robin-hood-hashing 3.11.5 的 `src/include/robin_hood.h` 中有：

```c
#if defined(__GNUC__) && __GNUC__ < 5
#    define ROBIN_HOOD_IS_TRIVIALLY_COPYABLE(...) __has_trivial_copy(__VA_ARGS__)
#else
#    define ROBIN_HOOD_IS_TRIVIALLY_COPYABLE(...) std::is_trivially_copyable<__VA_ARGS__>::value
#endif
```

clang 编译器预定义 `__GNUC__=4`（兼容 GNU 语义），因此该分支被 clang 命中，
调用 `__has_trivial_copy`。clang 15+ 将该内建宏标记为 deprecated，配合
`-Werror,-Wdeprecated-builtins` 时报编译错误：

```
error: builtin __has_trivial_copy is deprecated; use __is_trivially_copyable instead [-Werror,-Wdeprecated-builtins]
```

## 根因

- clang 预定义 `__GNUC__=4` 使 `__GNUC__ < 5` 成立；
- clang 15+ 弃用 `__has_trivial_copy`；
- 上游为老 g++ 写的兼容分支没有排除 clang。

## 方案

把条件改为排除 clang：

```c
#if defined(__GNUC__) && __GNUC__ < 5 && !defined(__clang__)
#    define ROBIN_HOOD_IS_TRIVIALLY_COPYABLE(...) __has_trivial_copy(__VA_ARGS__)
#else
#    define ROBIN_HOOD_IS_TRIVIALLY_COPYABLE(...) std::is_trivially_copyable<__VA_ARGS__>::value
#endif
```

clang 一律走 `std::is_trivially_copyable` 标准 trait 分支（语义等价，
C++11 起可用，header-only 库要求 C++14 完全满足）。

补丁文件：`patches/0001-src-include-robin_hood.h.patch`。

## 验证

- 修复前：`clang++ -std=c++14 -Werror -Wdeprecated-builtins` 编译含该头的 TU 失败；
- 修复后：上游测试程序 `rh` 完整编译通过，127/127 test cases、
  2,164,686 assertions 零失败；
- `conan create`（含 patch 应用）成功，test_package 1/1 通过。

## 适用边界

- 所有在 clang 15+ 上编译、且含 `__GNUC__ < 5` 兼容分支或直接使用
  `__has_trivial_copy` 的 C/C++ 库；
- 常见于 header-only 哈希/容器库（robin-hood-hashing 系）；
- gcc 实际版本 < 5 的古老工具链不受影响（分支语义保留）。

## 反例与限制

- **禁止** `#define __has_trivial_copy` 或 `#undef` 编译器内建宏（UB）；
- 若库无法打补丁（第三方固定源码），可用 `-Wno-deprecated-builtins`
  临时绕过（不建议作为 PR 正式方案）。

## 查重差异

- 与 E198（`-Wdeprecated-copy`，类自定义赋值运算导致的拷贝构造警告）不同：
  E198 是隐式拷贝构造 vs 用户定义 operator= 的 C++ 语义问题，本文是编译器
  内建宏本身被弃用；
- 与 E540（OHOS runner PATH）无关。
