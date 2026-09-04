# DRAFT：C++11 下 OHOS libc++ 缺失 `std::is_null_pointer` 的 polyfill 方案

> Contributor: E201 (AtomCode) | Status: Draft | Updated: 2026-09-02
> Source: indirect-lite 0.1.0 适配（非 std-lite 家族, P1950 indirect_value 回移）

## 背景

indirect-lite 0.1.0 是 header-only CMake 库（INTERFACE library），上游声明支持 C++11
（测试即包含 `indirect-value-lite-cpp11.t` 目标）。在 HarmonyOS PC（OHOS 6.0，clang 15，
libc++-ohos）做 Conan 适配时，C++11 测试目标编译失败。

## 错误 1：`std::is_null_pointer` 在 C++11 模式下不存在

### 现象

```text
include/nonstd/indirect_value.hpp:1212:90: error: no template named 'is_null_pointer'
in namespace 'std'; did you mean 'is_pointer'?
（同一错误 12 处，全部位于 relational-operator 扩展的 enable_if）
```

### 根因

`std::is_null_pointer` 是 **C++14** 标准库特性。OHOS libc++（libcxx-ohos，
`ohos-sdk_26.0.0.18/ohos/native/llvm/include/libcxx-ohos/include/c++/v1/__type_traits/`）
严格按标准版本暴露 trait，`-std=c++11` 编译模式下不提供该模板。上游头文件声明支持
C++11，但扩展部分（`nsiv_CONFIG_NO_EXTENSION_RELATIONAL_OPERATORS` 默认 0=开启）直接使用
`std::is_null_pointer`，属于"声明 C++11 支持却使用 C++14 trait"的上游兼容性缺陷。

### 方案

头文件已有 `namespace std11 { }` polyfill 空间，在其内按语言标准分支补回退实现：

```cpp
namespace std11 {
#if nsiv_CPP14_OR_GREATER
    using std::is_null_pointer;
#else
    // std::is_null_pointer is C++14; provide a C++11 polyfill:
    template< typename T > struct is_null_pointer : std::is_same< typename std::remove_cv<T>::type, std::nullptr_t >{};
#endif
}
```

并将 12 处 relational-operator 的 `std::is_null_pointer<...>` 改为 `std11::is_null_pointer<...>`。

要点：
- 不改测试标准（不把 cpp11 目标整体提升到 C++17），保留库的 C++11 支持
- 不加任何平台宏（非 OHOS 专属修复，任何严格标准版本化的 libc++/libstdc++ 均适用）
- 修复位于库内 polyfill 命名空间，符合上游既有 std11/std14/std17 回移模式

### 验证

```bash
make -j2                    # cpp11/cpp14/cpp17/cpp20 全 Build 成功
ctest --output-on-failure   # 4/4 PASSED（54 个 lest CASE 全过）
conan create ...            # OHOS aarch64 干净构建 G2 通过，test_package PASS
```

### 与现有知识关系（四范围查重）

| 范围 | 结果 |
|---|---|
| graph E*.kv / doc E*.md | **部分覆盖 E130**（change-cxx-standard）。E130 覆盖 libcxx-ohos 下 C++11 编译失败的 nullptr_t/__abi_tag__/constexpr 家族，但方案是整体提升标准到 C++17；未覆盖 `is_null_pointer` 缺失这一具体 trait 错误，也未提供保留 C++11 的 polyfill 方案 → 新增差异 |
| index.tsv | 无直接条目 |
| drafts/* | 无重复草稿 |

路径初判：**B（知识库扩展）**——已验证、可跨库复用（nonstd-lite 家族及声明 C++11 支持的头文件库通用）。

### 适用范围

- 声明支持 C++11 且扩展/重载使用 C++14 trait（如 `std::is_null_pointer`）的头文件库
  在 OHOS libc++ / 严格标准版本化 libc++ / libstdc++ 上构建时
- 复用方式：头文件内建 polyfill 命名空间（如 `std11`），按 `__cplusplus` 或库自带
  版本宏分支提供回退，并统一替换扩展代码中的引用