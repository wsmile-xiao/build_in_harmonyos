# DRAFT-ohos-libcxx15-format-ranges-capability-gap

- **id**: DRAFT-ohos-libcxx15-format-ranges-capability-gap
- **阶段**: compilation
- **严重度**: 3 (blocking)
- **分类**: libcxx, toolchain, compat, cxx20, portability, libc
- **来源事件**: archives/m/microsoft-proxy/4.0.1 (patch 0001), 2026-09-02
- **作者**: pc1-20

## 错误特征

```
no member named 'formatter' in namespace 'std'
no member named 'uninitialized_copy' in namespace 'std::ranges'
no member named 'format_context' in namespace 'std'
no member named 'basic_format_parse_context' in namespace 'std'
```

## 根因

OHOS SDK26（ohos-sdk_26.0.0.18）配套 libc++ 15.0.4 在 `include/c++/v1/__config` 定义
`_LIBCPP_HAS_NO_INCOMPLETE_FORMAT` 与 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`：

- 官方 `<format>` 头**存在但其实现整体被 `#if` 关闭**（空 stub），
  `std::formatter` / `std::format_context` / `std::basic_format_parse_context` 均无声明；
  同时不隐式传递 `<string_view>`。
- `std::ranges::uninitialized_copy` / `for_each` 等 ranges 内存/算法不可用。
- 不提供 `<memory_resource>` 头。

用 `__has_include(<format>)` 探测会**误判为可用**（头存在但无内容），使依赖完整 C++20
标准库的库（如 microsoft/proxy）在 OHOS 上与 CI（完整 libc++）编译结果不一致。

## 修复方案（推荐，已验证，全工具链可编译）

1. 把 `#if __has_include(<format>)` 全部改为标准特性宏
   `#if defined(__cpp_lib_format) && __cpp_lib_format >= 202110L`
   （OHOS libc++ 不定义该宏 → format skill 自动禁用，符合标准语义）。
2. `std::ranges::uninitialized_copy(a, b)` → 等效经典算法
   `std::uninitialized_copy(std::begin(a), std::end(a), b)`
   （经典算法 OHOS libc++ 提供）。
3. 若依赖 `<format>` 隐式传递的 `<string_view>`，补直接 `#include <string_view>`。

补丁属 **libc 能力探测类（R8 例外）**，非平台宏，不改变完整工具链上的行为。

## 验证

- 复现：`/data/service/hnp/bin/clang++ -std=c++20 -c probe.cpp`（含 `std::formatter<int>`）→ 失败
- 修复后：`conan create . -pr:h ohos-aarch64 -pr:b default --build=missing` → exit 0；
  test_package `./example`（circle/square OK）与 `./ohos_test`（OHOS-specific PASS）均通过

## 适用范围

- 目标 OHOS SDK26 clang15/libc++15 的所有 C++20 项目
- include `<format>`、直接使用 ranges 内存算法、依赖 `<format>` 隐式 `<string_view>` 的库
- 上游测试中引用 `std::format` 的 gtest 用例（硬阻塞来源之一）

## 查重

- graph/index.tsv：无命中（E120/E130/E191/E247/E286/E306/E387/E455/E538 签名不同）
- knowledge/doc/：E130（nullptr_t/c++11）、E387（llvm-lit）、E455（libcxx conan profile）均不覆盖
- knowledge/graph/*.kv：无匹配 error_signature
- knowledge/drafts/：`DRAFT-libcxx15-missing-cpp20-spaceship` 为同工具链家族但
  **不同签名/修复**（operator<=> vs format+ranges 内存算法）→ 部分覆盖、新增差异

## 路径初判

路径 B（知识库扩展）：候选已验证、可跨库复用、查重未完全命中（仅兄弟草稿）。
草稿 .kv/.md 同 stem，与 microsoft-proxy 归档进入同一 PR。
