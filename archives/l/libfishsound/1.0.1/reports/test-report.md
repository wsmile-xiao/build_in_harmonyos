# libfishsound 1.0.1 测试报告（W3 本地 CI 模拟）

- 平台：OHOS aarch64 原生（clang 15，conan profile ohos-aarch64）
- 构建系统：autotools（conan create）
- 报告日期：2026-09-19
- 说明：本报告记录跨轮稳定的测试事实；逐轮日志哈希与验证轮 HEAD
  由任务侧审计材料（test-template-check.md 与 finish 证据回执）绑定，
  原始日志位于设备工作树 reports/（不入仓）。

## 上游官方测试（make check，src/tests/，4 个测试程序）

| # | 测试程序 | 结果 |
|---|----------|------|
| 1 | comment-test | PASS |
| 2 | noop | PASS |
| 3 | encdec-comments | PASS |
| 4 | encdec-audio | PASS |

automake test summary：TOTAL 4，PASS 4，FAIL 0，SKIP 0，ERROR 0。
上游通过率 4/4（100%）。未修改任何上游测试。

## test_package 消费者测试（test_libfishsound，1/1 Passed）

ctest：`1/1 Test #1: test_libfishsound ... Passed`，`100% tests passed`。

逐编解码器回环（Vorbis 44100Hz 双声道、Speex 8000Hz 单声道，各 4×256 帧，
按上游 encdec-audio 同款方式以 prepare_truncation EOS 收尾）：

```
---- Vorbis: encoded 1024 frames in 12 packets, decoded 1024 frames
---- Speex: encoded 1024 frames in 6 packets, decoded 1280 frames
libfishsound consumer test: all checks passed
```

Vorbis 精确回环（1024→1024）；Speex 按 320 帧窗口补齐（1024→1280，
与上游期望公式一致）。13 个 CHECK 断言点 × 2 编解码器 = 26 断言全部
通过，失败 0，跳过 0。

## 证据文件

- reports/w3-local-ci.log：W3 全量日志（automake 汇总 + ctest 输出）
- reports/conan-verify-report.md：G0–G4/L2/L4/L5 门禁结果
- .ci-result.json：finish 写入，含 conan create 日志 SHA256（防伪造）
- 逐轮哈希绑定：任务侧 test-template-check.md 与 evidence/ 回执

## 结论

编译通过；上游测试 4/4，消费者测试 1/1；无失败、无跳过。
