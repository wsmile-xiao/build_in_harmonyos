# aarch64 上 plain char 默认 unsigned 触发库内 is_unsigned_v 复校验分支，char 字符串解析误抛 parser_error（libenvpp 等 C++ 解析库）

> **结构化数据**: [knowledge/drafts/DRAFT-libenvpp-1.5.3-char-unsigned-revalidation.kv](DRAFT-libenvpp-1.5.3-char-unsigned-revalidation.kv)
> **严重度**: 🟡 medium | **阶段**: testing | **工具**: clang / CMake / 上游测试二进制
> **来源**: libenvpp 1.5.3 R01 上游测试 81 用例/756 断言实测（2026-09-22）

---

## 问题现象

在 aarch64（含 OHOS）默认无符号 `plain char` 的目标上运行 libenvpp 1.5.3 上游
Catch2 测试套件（`libenvpp_tests`），**81 测试用例中 1 用例失败 / 756 断言中
3 个失败**，全部集中于 char 类型解析：

- `libenvpp_parser_test.cpp` "Leading and trailing whitespaces"：
  `test_parser<char>("a", 'a')`、`test_parser<char>("A", 'A')`、
  `test_parser<char>("a ", 'a')` —— 均抛异常：

```
due to unexpected exception with message:
  Failed to validate whether 'a' was correctly parsed as 'a'
```

关键细节：**非 char 类型（int/float/bool/string 等）全部通过**，只有字符类型失败。

## 根因

C/C++ 中 plain `char` 的符号性由实现定义。**aarch64（含 OHOS，AAPCS64）默认 plain
`char` 为无符号（0..255）**，`std::is_unsigned_v<char>` 为 true（x86-64 上游开发机为
false）。libenvpp 的 `detail::construct_from_string<T>` 解析内建类型后有一段
"unsigned 数值复校验" 逻辑：

```cpp
if constexpr (!std::is_same_v<T, bool> && std::is_unsigned_v<T>) {
    auto signed_parsed = std::int64_t{};
    auto signed_stream = std::istringstream(std::string(str));
    signed_stream >> signed_parsed;   // 把整串按 int64 重新解析
    // fail → throw parser_error
}
```

该分支本意是校验 `unsigned int` 等**整型**是否被负数/溢出静默吸收（如把 "-1" 解析为
无符号整型不应静默变成 4294967295）。但 `char` 在 aarch64 上 `is_unsigned_v` 为 true，
"a"/"A" 显然无法按 int64 解析 → 误抛 `parser_error`。问题在 x86-64 上因 char 有符号
而完全不可见。

## 修复方案（本次采用）

以 patches 补丁形式修改库源码 `include/libenvpp/detail/parser.hpp`，在 unsigned
复校验分支中排除字符类型：

```diff
-    if constexpr (!std::is_same_v<T, bool> && std::is_unsigned_v<T>) {
+    if constexpr (!std::is_same_v<T, bool> && std::is_unsigned_v<T> && !std::is_same_v<T, char>
+                  && !std::is_same_v<T, signed char> && !std::is_same_v<T, unsigned char>) {
```

修复后重跑全量上游测试：**81/81 用例、756/756 断言全绿**，test_package 消费者测试
（char 值注入解析）也通过。

## 触发条件 / 验证方法

- 触发：目标平台 plain `char` 默认无符号（aarch64/OHOS/ARM32/RISC-V），且解析库用
  `std::is_unsigned_v` 做整型/字符复校验分支，char 输入参与字符串解析。
- 验证：`#include <type_traits>` 打印 `is_unsigned_v<char>`（1=触发面）；重跑上游完整
  测试套件（全量断言，非单测）；重跑 test_package 消费者测试。

## 适用边界

- 适用：使用 `std::is_unsigned_v`（或等价 traits）做数值复校验的 C++ 字符串解析库。
- **不适用 / 已区分**：同源于 "aarch64 char 无符号" 的他类问题走各自既有条目：
  - E419（librasterlite2）：char 作为有符号 8 位样本、INT8 API 数值差 256 → `-fsigned-char` 工具链修复；
  - DRAFT-clipp（1.2.3）：strtoll+clamp 负值钳位为 0 → 平台差异如实上报/控制组；
  - DRAFT-8543（looktxt）：getc()/fgetc() EOF 哨兵存入 char 导致死循环 → 接收变量拓宽为 int；
  - DRAFT-9645（polyseed）：`*p < 0` 判非 ASCII 静默失效 → `-fsigned-char` 重编。
  本条目专指**库内数值复校验分支误纳字符类型**，修复是**源码补丁排除 char 族**，与上述不同。

## 反例 / 限制

- 不作平台宏（`__OHOS__`）分叉（R8）：问题本质是类型特征分支，非 OS 差异。
- 不修改上游断言、不禁用测试（R6）：如实复验。
- `-fsigned-char` 可作 fallback 但会改变整个翻译单元 char 语义，库源码补丁是更精确的最小修复。