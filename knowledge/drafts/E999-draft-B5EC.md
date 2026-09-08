# E999 — OHOS libc++ 未实现 std::string_view 的 operator<=>（三路比较）

## 现象

C++20 代码中对两个 `std::string_view` 使用三路比较（`<=>`）在 OHOS 工具链上编译失败：

```
error: invalid operands to binary expression ('std::string_view' (aka 'basic_string_view<char>') and 'std::string_view')
    return std::string_view{lhs.name.data(), lhs.name.size()} <=> std::string_view{rhs.data(), rhs.size()};
```

候选函数提示里没有任何 `operator<=>` 重载可匹配 string_view。

## 根因

OHOS SDK（26.0.0.18，clang 15 工具链）自带的 libc++ 头文件没有实现
`std::basic_string_view` 的三路比较运算符（上游 libc++ 在更高版本才提供）。
任何 C++20 库只要对 string_view 用 `<=>` 就会失败。这不是代码 bug，
是工具链标准库能力缺口。

## 修复

把 `sv <=> sv` 改写为 `sv.compare(other) <=> 0`：

```cpp
// 原代码
return std::string_view{lhs.name.data(), lhs.name.size()} <=> std::string_view{rhs.data(), rhs.size()};
// 修复后
return std::string_view{lhs.name.data(), lhs.name.size()}.compare(std::string_view{rhs.data(), rhs.size()}) <=> 0;
```

`compare()` 返回 `int`，内置整型 `<=>` 在 clang 15 上完全可用，且
`int <=> 0` 的结果类型是 `std::strong_ordering`，与原表达式语义一致，
调用方（`std::is_eq` / `std::less` 等）不受影响。

## 禁止

- ❌ 降回 `-std=c++17`：库内其他 C++20 特性（如 `std::span`）会连锁失败。
- ❌ 手写 `operator<=>` 重载注入 `namespace std`：UB（向 std 添加重载）。

## 实证案例

- kcodecs 6.26.0（2026-09-05）：`src/kcharsets.cpp` 的
  `operator<=>(const Entity&, std::span<const char, N>)`，补丁
  `0005-src-kcharsets.cpp.patch`，修复后编译+全部上游测试通过。

## 相关

- 另一个 6.26.0 新坑（未单列条目）：KDE 上游测试若不链接主库目标，
  `target_compile_features(KF6Codecs PUBLIC cxx_std_20)` 不会传播，
  测试以 -std=c++17 编译导致 `std::span` 失败——对该测试目标显式
  `target_compile_features(<target> PRIVATE cxx_std_20)` 即可
  （kcodecs patch 0004）。
