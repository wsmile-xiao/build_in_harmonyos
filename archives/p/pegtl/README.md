# pegtl

**Parsing Expression Grammar Template Library**

PEGTL 是一个现代 C++ 解析器库，基于 Parsing Expression Grammar (PEG) 技术。

## 基本信息

- **版本**: 4.0.0
- **许可证**: Boost Software License 1.0
- **网站**: https://github.com/taocpp/PEGTL
- **类型**: Header-only 库

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|---------|--------|
| 4.0.0 | built | 2026-06-08 | 0 |

## 特性

- Header-only 设计，无需编译链接
- 支持 C++17 标准
- 提供丰富的内置规则和动作
- 支持流式输入、文件输入等多种输入类型
- 提供调试和追踪工具

## 使用方法

pegte 是 header-only 库，只需包含头文件即可使用：

```cpp
#include <tao/pegtl.hpp>
```

## 安装位置

- 头文件: `/usr/local/include/tao/pegtl.hpp`
- pkg-config: `pegtl.pc` (在 `/usr/local/share/pkgconfig/`)
- cmake 配置: `/usr/local/share/pegtl/cmake/`

## 编译注意事项

1. pegtl 是 header-only 库，主要只需安装头文件
2. 测试和示例程序需要完整的 C++ 标准库支持
3. 编译时需设置 `-DPEGTL_BUILD_TESTS=OFF` 和 `-DPEGTL_BUILD_EXAMPLES=OFF`
4. 要求 C++17 或更高标准

## 依赖

- 无外部依赖（仅需 C++17 编译器）