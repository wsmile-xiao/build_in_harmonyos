# dragonbox

Dragonbox 是一个快速且精确的浮点数到十进制字符串转换算法库。

## 描述

Dragonbox 由 Junekey Jeon 开发，是 Ryu 算法的改进版本，提供了从 IEEE 754 浮点数到十进制字符串的最短表示转换。该算法在保证正确性的前提下，通过优化的整数运算和缓存表实现了极高的性能。

## 组件

- **dragonbox**: 仅头文件库 (header-only)，提供核心浮点到十进制转换算法
- **dragonbox_to_chars**: 静态库，提供 `dragonbox_to_chars` 函数将浮点数直接转换为字符串

## 构建系统

- CMake (>= 3.14)
- C++17 标准

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.1.3 | built | 2026-06-18 |

## 许可证

- Apache 2.0 (LLVM 例外)
- Boost Software License 1.0

## 上游

- GitHub: https://github.com/jk-jeon/dragonbox
