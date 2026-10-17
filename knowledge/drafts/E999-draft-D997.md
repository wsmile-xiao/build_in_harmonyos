# E999 — OHOS SDK libcxx-ohos 缺少 C++20 `<source_location>` 头

## 错误特征

```
fatal error: 'source_location' file not found
#include <source_location>
         ^~~~~~~~~~~~~~~~~
1 error generated.
```

- 触发工具: clang (OHOS SDK 自带，clang 15.0.4)
- 阶段: compilation

## 触发条件

- 构建系统: CMake（`CMAKE_CXX_STANDARD 20/2b` 或更高）
- 工具链: OHOS SDK `libcxx-ohos/include/c++/v1`（`_LIBCPP_VERSION 15004` 裁剪版 libc++）
- 代码: 测试/示例等用户代码使用 `std::source_location`（如 `std::source_location::current()` 作
  默认参数，仅用 `file_name()` / `line()`）

## 根因分析

OHOS SDK 自带的 libc++（libcxx-ohos，`_LIBCPP_VERSION 15004`）是裁剪版：头文件仅 170 个
（完整 libc++ 15 应有 500+），`<source_location>` 头未随附。clang 15 本身支持 C++20 的
`source_location` 语言特性，但标准库头缺失导致 `#include <source_location>` 直接
`file not found`。这不是编译标志问题（`-std=c++20/2b` 均可通过），而是标准库头裁剪。

## 解决方案

### 推荐方案

在测试/用户代码中以 `__has_include(<source_location>)` 探测；缺失时提供最小
`std::source_location` shim，`current()` 用 `__builtin_FILE/FUNCTION/LINE/COLUMN`
实现，`file_name()/function_name()/line()/column()` 按实际使用成员补齐（cppp-reiconv
仅用 `file_name()` 与 `line()`）。只补测试代码，不动库本体。

```cpp
#include <cstdint>
#if __has_include(<source_location>)
#include <source_location>
#else
namespace std {
struct source_location {
    static constexpr source_location current(
        const char *file = __builtin_FILE(),
        const char *func = __builtin_FUNCTION(),
        std::uint_least32_t line = __builtin_LINE(),
        std::uint_least32_t col = 0) noexcept { /* ... */ }
    constexpr const char *file_name() const noexcept { return file_; }
    constexpr std::uint_least32_t line() const noexcept { return line_; }
    /* ... */
};
}
#endif
```

### 禁止做法

- ❌ 不要修改 OHOS SDK 的 libcxx-ohos 头（系统目录，且 erofs/权限受限）
- ❌ 不要为整个库切换 `-stdlib=libstdc++`（OHOS 无 libstdc++，且引入 ABI 不一致）
- ❌ 不要把 `source_location` 用法整个删掉/改为空壳（会掩盖诊断信息）

## 验证

```bash
# 修复前（应输出 ≥1，证明头缺失）
clang++ -std=c++20 -E -x c++ - <<< "#include <source_location>" 2>&1 | grep -c "file not found"
# 修复后
ctest --output-on-failure   # cppp-reiconv 141/141 全量通过
```

## 关联条目

- 相似: E313（musl 缺 C23 stdckdint.h 的 shim 思路），但触发面不同（C++20 头 vs C23 头）
- 来源: cppp-reiconv 3.0.0 适配（补丁 `0001-tests-output.hpp.patch`）
