# DRAFT-embedded-cli-0.1.4-consumer-test-callback-tokenize

> 草稿（Path B 知识库扩展候选），由 embedded-cli 0.1.4 消费者测试两个
> 真实失败（binding 回调未触发、tokenize 参数截断）与已验证修复产生。
> 本文与同名 `.kv` 配对，逐字段一致。仅为本地知识草稿。

## topic

回调驱动 CLI 库消费者测试：embeddedCliProcess 需先设置 writeChar 输出回调；tokenizeArgs=true 回调收到 tokenize 串需用公开 token API 读取

## error_signature

1. 消费者测试（仅用公开 API 创建 CLI、绑定命令、注入 `"cmd args\r\n"`）后
   binding 回调从未触发，断言失败。
2. 设置回调后依旧失败：回调内 `snprintf("%s", args)` 只得到首个 token
   （期望 `"1 1"`，实际 `"1"`）。

## root_cause

1. `embeddedCliProcess()` 在 `cli->writeChar == NULL` 时直接 `return`，
   rx 缓冲永不被处理；库的上游测试包装类（CliWrapper）在构造时设置
   writeChar，裸消费者容易漏掉该前置条件。
2. `tokenizeArgs=true` 时 binding 回调收到的 `args` 是 tokenize 后的字符串：
   token 之间为单 0x00，列表以双 0x00 结尾；C 字符串 API 读到首个 0x00 即截断。

## durable_solution

1. 消费者在 `embeddedCliProcess()` 之前必须设置输出回调（sink 即可）：
   ```c
   cli->writeChar = sink_write_char; // 空 sink 也满足前置条件
   ```
2. 对 tokenize 串用公开 token API 逐项读取并断言：
   ```c
   embeddedCliGetToken(args, 1); embeddedCliGetToken(args, 2); // 不带分隔符
   embeddedCliGetTokenCount(args); embeddedCliFindToken(args, tok);
   ```
   不要直接 `snprintf("%s", args)` 或多 token 拼接。
3. 以真实命令注入（`embeddedCliReceiveChar` + `embeddedCliProcess`）验证绑定触发。

## impact

任何直接以公开 C API 消费该库（无上游包装类）的消费者测试都会命中
writeChar 前置条件与 tokenize 串格式两个坑；同类回调驱动 CLI 库也适用
"输出回调前置条件 + 用库公开解析 API 读参数" 的测试模式。

## evidence_references

- embedded-cli 0.1.4 test_package/test.c（消费者验证）与
  test_package/ohos_static_alloc_test.c（鸿蒙专项：静态分配 + tokenize API）：
  conan-verify G2 test_package 2/2 Passed
- conan-create.log 首错：`FAIL: binding callback was not fired` → 修复后
  `PASS: ... binding fired, tokens=1/1, tokenize api ok`

## recovery_condition

不适用（测试修复，无恢复动作）；后续该库消费者测试按上述模式编写即可。

## status

draft_pending_review