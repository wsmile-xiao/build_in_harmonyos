# libopenv2g 0.9.5 测试报告

## 结论

- **Conan test_package**：1/1 测试程序通过，13/13 `CHECK-OK` 断言通过（100%）。
- **上游正式测试**：0 个；上游 ZIP 没有 tests/、CTest 注册或 `make check` 目标。
- **上游示例**：未作为库包测试。`src/test` 示例在目标机完成协议输出后以 SIGSEGV 结束，故不把该交互式示例的失败误报为库 API 失败。

## 验证命令

```text
conan create archives/l/libopenv2g/0.9.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable

python3 scripts/ohc-run.py conan-verify libopenv2g 0.9.5 --profile ohos-aarch64
```

## 消费者测试覆盖

`test_package/test.c` 真实链接 `libopenv2g::libopenv2g`，检查：

1. EXI 位流写入、flush、读取 round-trip；
2. V2GTP header 写入、版本字段和 payload 长度；
3. 应用握手 EXI 编码、解码及协议字段 round-trip。

原始完整输出见 `conan-create.log`；门禁汇总见 `conan-verify-report.md`。测试程序在 HarmonyOS PC arm64 上运行通过。
