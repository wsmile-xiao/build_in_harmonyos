# tiny-utf8

Unicode (UTF-8) capable std::string — header-only C++11 library.

## 简介

tiny-utf8 是一个纯头文件的 C++11 字符串库，提供 UTF-8 感知的字符串类型
`tiny_utf8::string`（`basic_string<char32_t, char>` 的 typedef）。与标准库
`std::string`（按字节）不同，其 `length()` 返回码点个数、`size()` 返回字节数，
迭代器与 `operator[]` 均按码点工作，支持 CJK、Emoji 等任意 Unicode 文本。

## OHOS 适配

- **构建系统**: CMake（header-only INTERFACE target），Conan 配方为 header-library
- **依赖**: 无（库本身零依赖；gtest/gmock 1.17.0 仅测试期使用）
- **命名空间**: `tiny_utf8`（注意下划线，非 `tinyutf8`）
- **版本**: 4.4.3（官方 tag v4.4.3，SHA-256 见 conandata.yml）
- **验证**: 上游 GoogleTest 16/16 通过；OHOS aarch64 工具链 conan create 通过

## 使用

```cpp
#include <tinyutf8/tinyutf8.h>
tiny_utf8::string s(u8"Hello, 世界!");
s.length();  // 10 (码点)
s.size();    // 14 (字节)
```

通过 CMake：`find_package(tinyutf8)` + 链接 `tinyutf8::tinyutf8`。
