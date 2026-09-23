# DRAFT-cpp-can-parser-1.0.0-stringtokenizer-assignment-comparison：字符串 tokenizer 把赋值误当比较

> Contributor: AtomCode (pc2-2) | Status: Draft | Updated: 2026-09-05
> Source: cpp-can-parser 1.0.0 HarmonyOS PC adaptation（R01，patch 0002-src-parsing-Tokenizer.cpp.patch）
> 对应：knowledge/drafts/DRAFT-cpp-can-parser-1.0.0-stringtokenizer-assignment-comparison.kv

## 现象

以 `CppCAN::CANDatabase::fromString()` 解析内嵌 DBC 时抛异常（消费者测试真实复现）：

```text
libc++abi: terminating due to uncaught exception of type CppCAN::CANDatabaseException:
Syntax error: Expected "BS_" but got "" at line 482
```

行号 482 远超输入 DBC 文本的约 40 行，且解析器始终只见到空 token。

## 根因

`src/parsing/Tokenizer.cpp` 的字符串入口 `StringTokenizer::doGetNextChar()`：

```cpp
char result = src_str[charCnt++];
if (result = '\n') {   // BUG: 赋值恒真，result 被覆盖为 '\n'
  addLine = true;
}
return result;          // 永远返回 '\n'
```

赋值表达式 `'\n'` 非零恒真，每次取字符后 `result` 被改写为换行符、`addLine` 恒置位
（行计数随字符数膨胀），解析器实际只见换行，任何字符串解析必然失败。
对照同文件文件入口 `FileTokenizer::doGetNextChar()` 的等价逻辑为正确的 `==`
（`if (result == '\n')`），证明是上游笔误。该缺陷让 `fromString()` 这条公开 API
在 v1.0.0 tag 上完全不可用，而文件入口（`fromFile`/上游测试）不受影响，
极具迷惑性。构建期仅报 `-Wparentheses` 警告不报错，易被忽略。

## 验证（真实证据）

- 修复前：conan create 时 test_package 的 test_consumer 抛上述异常（Signal 6，
  conan_create.log 前段）；上游 `cpc-test-parsing` 只走 fromFile 不受影响
- 修复后（`=` → `==`）：conan create rc=0；test_consumer 输出
  `consumer_check: ALL PASSED`；harmonyos_specific_test 输出
  `harmonyos_specific_test OK: platform=OHOS(aarch64)，__OHOS__/__aarch64__ defined`；
  上游 cpc-test-parsing 回归 rc=0（日志: conan_create.log、ctest_full.log，
  sha256 见 evidence_sha256.txt）

## 适用边界

- 触发面：任何上游代码把赋值误当比较（`if (x = <常量>)`、`while (c = f())`），
  尤其是字符串/字符流 tokenizer 与双入口（文件+字符串）解析器
- 反例：赋值语义确实需要、且右值为变量（如 `while ((c = getchar()) != EOF)`）
  不是缺陷，需显式括号保留；修复仅针对恒真覆写型笔误
- 推广价值：跨库可复用——1 行修复 + 用字符串源入口做端到端回归的完整诊断路径

## 查重

四范围（正式 knowledge/graph/*.kv、index.tsv、knowledge/drafts/、graph engine）
均未命中同类条目（engine 对错误签名仅返回 E169/E291 等无关条目）；与 E217
（CMake 头文件子目录安装）causal/solution 均无关。七轴查重详见
archives/c/cpp-can-parser/1.0.0/reports/knowledge_candidate_ledger.md（候选 A）。