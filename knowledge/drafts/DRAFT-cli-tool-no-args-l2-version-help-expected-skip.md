# DRAFT: 无 CLI 参数的工具包 L2 探测预期降级为 skip（version/help failed）——不要伪造旗标

- 发现于：tinymembench/0.4 真机 shadow CI r6（2026-09-29，全绿轮）
- 触发面：所有**入口为 `int main(void)`、不解析命令行参数**的
  benchmark/工具类包

## 现象

门禁结果中出现：

```
L2_RESULT=skip: <库名> version/help failed
```

其余 G0/L0/L1/L4/L5 全 pass，Pass rate 100%，exit 0。构建 Summary 不
计为失败。

## 根因

L2 bin smoke test 会用 `--version` / `--help`（或 `-v`/`-h`）探测包内
bin/ 可执行文件，判断其"可执行且行为正常"。对入口为
`int main(void)`、完全忽略 argv 的工具（benchmark、演示程序等），
`./tool --version` 与无参运行等价：直接进入主流程（tinymembench 是
跑完整内存测试），探测逻辑拿不到版本/帮助输出，判定探测失败 →
L2 降级为 skip（不是 fail）。

## 解法（重要：这是预期行为，不要"修复"）

- **接受 skip**：`skip: version/help failed` 与 `skip: no bin/ dir`
  同级，是合规的降级路径，Summary 仍 100%。
- **禁止伪造**：不要给上游加 `--version` 参数支持补丁、不要在
  test_package 里替答——上游行为就是无参数设计，为过门禁改行为属于
  本末倒置，且可能引入上游 diff。
- 在 notes/PR 中说明一句：工具无 CLI 参数解析（引 main(void) 证据），
  L2 skip 属预期。

## 验证

tinymembench/0.4：`main(void)` 无参数解析，`--version` 被忽略直接
跑 benchmark；r6 门禁 `L2_RESULT=skip: tinymembench version/help
failed`，同时 L1（test_package 完整 benchmark 断言 22 条带宽行 +
延迟段 + exit 0）pass——功能验证由 L1 承担，L2 skip 无损结论。
