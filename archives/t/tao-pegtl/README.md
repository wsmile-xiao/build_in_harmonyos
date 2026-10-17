# tao-pegtl

**Parsing Expression Grammar Template Library**

PEGTL 是一个现代 C++17 解析器库，基于 Parsing Expression Grammar (PEG) 技术，纯 header-only。

## 基本信息

- **版本**: 3.2.8
- **许可证**: MIT
- **网站**: https://github.com/taocpp/PEGTL
- **类型**: Header-only 库

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|---------|--------|
| 3.2.8 | built | 2026-09-08 | 0 |

## 特性

- header-only，零编译依赖（C++17 标准库即可）
- 完整 PEG 组合子（seq/sor/plus/star/must 等）
- 支持 UTF-8/16/32 与字节流输入
- contrib 模块提供 JSON/URI/HTTP 等常用文法
- 上游 ctest 128/128 全通过（R51 实测）

## 历史

- 仓库另有 `archives/p/pegtl/4.0.0`（同上游不同条目）。