# DRAFT — C 字符串输入语义库的消费者测试向量需避免嵌入 NUL

## 问题

libbaseencode 1.0.15（RFC-4648 base32/base64 编解码库）的 HarmonyOS 专项测试中，
1 MiB 大输入 round-trip 出现 `base64 1MiB round-trip 一致` 断言失败，而 base32 相同
输入通过。同库两个编码器行为不一致。

## 根因

`base64_encode()`（src/base64.c）在输入**任意位置**遇到 `\0` 即停止计数：

```c
if (user_data[i] != '\0') { total_bits += 8; user_data_chars += 1; }
else { break; }
```

`base32_encode()`（src/base32.c）仅当 `\0` 位于 `data_len-1`（末尾）才 break，
中间 0x00 会正常计入：

```c
if (user_data[i] == '\0' && i == data_len-1) { break; }
else { total_bits += 8; user_data_chars += 1; }
```

即输入按 **NUL 结尾 C 字符串**语义处理。测试向量若含内嵌 0x00 字节：
- base64 只编码截断前缀（0x00 之前），解码结果长度回不到原输入 → round-trip 失败；
- base32 会编码全部字节（仅末尾 NUL 截断）→ round-trip 通过。

## 方案

1. 消费者/专项测试的二进制输入向量**禁止内嵌 0x00**（值域用 `1 + (i % 254)` 等），
   与库的 C 字符串输入语义对齐；
2. 大输入（1 MiB）round-trip 是有效的消费者验证手段，但必须先确认测试向量不含 NUL；
3. 同库多个 API 对嵌入 NUL 的截断位置语义可能不一致（base64 任意位置 vs base32 仅末尾），
   需分别验证，不能以一个通过推断另一个。

## 验证

- 修正前：`FAIL: large: base64 1MiB round-trip 一致`（base32 PASS）；
- 修正后（值域 1..254 无 NUL）：OHOS 专项测试 11/11 全 PASS；
- test_package/test.c 同步修正（v3 向量去掉内嵌 0x00）；
- 上游 29/29、conan-verify G1-G4 全 PASS。

## 适用边界 / 反例

- **适用**：按 NUL 结尾 C 字符串处理输入的 C 库（编解码类、字符串处理类）的
  消费者测试、test_package、上游测试移植。
- **不适用**：长度前缀式 API（显式支持嵌入 NUL）的库。
- **库特定行为**：base32 与 base64 的截断位置差异（任意位置 vs 仅末尾）是
  libbaseencode 特有实现，不可推广到其他库；但"嵌入 NUL 会截断"这一通用约束可复用。

## 查重差异（七轴）

- exact_duplicate: false（index.tsv/doc 无命中）
- causal_duplicate: false（E040 mandb 空指针崩溃、E231 测试发现未绑定校验包，均不同根因域）
- trigger_overlap: partial（E252/E244 同为"写消费者测试"，但错误特征不同）
- solution_overlap: no（无既有条目提出"避免嵌入 NUL 向量 + 记录 C 字符串输入语义"）
- combination_novelty: true（base64 任意位置 vs base32 仅末尾的截断语义差异为本任务独有观察）
- boundary_novelty: true（补充适用/不适用边界）
- test_migration_novelty: true（对测试移植给出可操作规则 + 1MiB 实测证据）

## 关系

- similar_to: E252（消费者测试实质化，trigger 层面重叠）
- caused_by: 无 / prerequisite_of: 无 / conflicts_with: 无

---
*草稿由 pc2-38 于 2026-09-27 建立（路径 B，随 libbaseencode 归档同一 PR 提交）*
