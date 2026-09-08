# DRAFT-jsonifier-ohos-libcxx-missing-std-headers — OHOS libc++ 缺失标准头

- **严重度**: 2（🟡 medium）
- **类别**: platform, portability, headers
- **触发工具**: clang/clang++（编译阶段）
- **来源库**: jsonifier 0.9.97（OHOS aarch64 适配，2026-09-03）

## 错误特征

```
/.../Allocator.hpp:27:10: fatal error: 'memory_resource' file not found
/.../Reflection.hpp:29:10: fatal error: 'source_location' file not found
```

## 根因分析

OHOS SDK（ohos-sdk_26.0.0.18）的 libcxx-ohos 定制 libc++ 头集合
（`llvm/include/libcxx-ohos/include/c++/v1/`）不提供标准 `<memory_resource>`
（仅有 `experimental/memory_resource`）与 `<source_location>`。C++17/C++20 库
直接 `#include` 这两个头时编译中断。

## 推荐方案

补丁两处（patches/ 落盘）：
1. `<memory_resource>`：改为 `#if __has_include(<memory_resource>) #include <memory_resource> #endif`
   ——库实际未使用 pmr 类型时仅需守卫，语义零变化。
2. `<source_location>`：新增 `Compat/SourceLocation.hpp` shim，API 与
   `std::source_location` 一致（`file_name()/function_name()/line()/column()/current()`），
   基于 clang 内建 `__builtin_FILE/FUNCTION/LINE`；被引文件统一改引 shim。

**验证**: conan create（ohos-aarch64 profile）+ 上游测试 211 用例 + 专项测试全部通过。

## 适用边界

任意 C++17/C++20 库落地 OHOS aarch64 时若直接 include 这两个标准头；shim 只补 API，
不改变 `std::source_location` 语义（标准库存在时由标准库提供）。

## 查重差异（四范围）

| 范围 | 结果 |
|------|------|
| index.tsv / doc/ | E130 相关（libcxx-ohos 定制标准库，但仅"变更 -std 标准"层面），未覆盖具体缺失头，未命中 |
| graph/*.kv | 无匹配 |
| drafts/ | 无匹配 |

→ **路径 B（知识库扩展）**：随 jsonifier 归档同 PR 交付。
