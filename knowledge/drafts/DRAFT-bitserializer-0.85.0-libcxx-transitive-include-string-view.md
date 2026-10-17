# DRAFT-bitserializer-0.85.0-libcxx-transitive-include-string-view

## 问题 (Problem)

bitserializer 0.85.0 的 `conan create`（test_package 消费者视角编译）时报：

```
include/bitserializer/common/text.h:71:7: error: variable has incomplete type 'void'
  void TrimWhitespace(std::basic_string_view<TChar, TTraits>& str)
error: no member named 'basic_string_view' in namespace 'std'
```

`text.h` 只 `#include <cstddef>` 却直接使用 `std::basic_string_view`，
依赖其它标准头（`<string>` 等）传递包含 `<string_view>`；该写法在
OHOS 的 libcxx-ohos 上失效。

## 根因 (Root Cause)

libcxx-ohos（OHOS SDK 26.0.0.18）裁剪了传递包含（transitive include），
上游头文件未显式 include `<string_view>` 时，`std::basic_string_view`
不可见。标准 libc++ / libstdc++ 通常经 `<string>` 等头间接注入
`<string_view>`，掩盖了上游的 include 缺失；OHOS 裁剪后暴露。

## 方案 (Solution)

在使用 `std::basic_string_view` 的头文件顶部显式补 include：

```cpp
#pragma once
#include <cstddef>
#include <string_view>
```

已固化为 `archives/b/bitserializer/0.85.0/patches/0002-include-bitserializer-common-text.h.patch`，
conandata.yml 声明，干净构建时自动应用。

## 验证 (Verification)

- `conan create`（ohos-aarch64 profile）+ test_package 消费者编译通过。
- 上游单元测试 860/860 通过（ctest）。
- conan-verify G0-G4/L2/L4/L5 全部通过。

## 适用边界 (Applicability)

- 触发条件：C++17 头文件直接使用 std::string_view / basic_string_view 但未
  显式 include `<string_view>`，且目标平台为裁剪传递包含的 libc++（OHOS）。
- 不适用：已显式 include `<string_view>` 的库；标准 libc++/libstdc++ 环境
  （传递包含通常可用，补 include 亦无害）。
- 反例：用 `using namespace std;` 或 typedef 掩盖——修复不彻底。

## 限制 (Limitations)

补齐 `<string_view>` 后，若库同时面向 C++14 及以下需加 `__has_include`
守卫；本库要求 C++17（CMakeLists `CMAKE_CXX_STANDARD 17`），无需守卫。
