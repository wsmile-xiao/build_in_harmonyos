# DRAFT-jsonifier-char-traits-partial-spec-ambiguity — aarch64 默认 unsigned char 导致模板部分特化歧义

- **严重度**: 2（🟡 medium）
- **类别**: platform, portability
- **触发工具**: clang/clang++（编译阶段）
- **来源库**: jsonifier 0.9.97（OHOS aarch64 适配，2026-09-03）

## 错误特征

```
error: ambiguous partial specializations of 'char_traits<const char>'
```

## 根因分析

aarch64（OHOS）默认 plain char 为 unsigned。jsonifier 的 `char_traits` 模板同时
按两个概念分派部分特化：`not_uint8_t`（`!std::same_as<unwrap_t<T>, uint8_t>`）与
`uint8_type`（`sizeof==1 && std::unsigned_integral`）。在 aarch64 上纯 `char` 同时
满足两个约束（char 是 1 字节 unsigned），导致 `char_traits<const char>` 实例化歧义；
x86 上 char 为 signed，不触发。

## 推荐方案

补丁（patches/ 落盘）：将 `uint8_type` 特化改为
`template<jsonifier::concepts::uint8_type T> requires (!std::same_as<unwrap_t<T>, char>)
class char_traits<T>` ——排除纯 char，使 char 只匹配 `not_uint8_t` 特化
（继承 `std::char_traits<char>`），消除歧义且不改类型语义。

**验证**: conan create（ohos-aarch64 profile）+ 上游整数/无符号 102 用例 + 专项测试全部通过。

## 适用边界

任意 C++ 库以 char/uint8_t 语义分派模板部分特化（char_traits 等），且目标平台
默认 char 为 unsigned（aarch64/ARM 系列）。

## 查重差异（四范围）

| 范围 | 结果 |
|------|------|
| index.tsv / doc/ | E419 相关（plain char signedness 影响 API 结果，C 语言/-fsigned-char 层面），未覆盖 C++ 模板部分特化歧义，未命中 |
| graph/*.kv | 无匹配 |
| drafts/ | 无匹配 |

→ **路径 B（知识库扩展）**：随 jsonifier 归档同 PR 交付。