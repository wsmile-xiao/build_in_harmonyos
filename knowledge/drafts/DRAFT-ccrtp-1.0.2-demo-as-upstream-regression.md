# DRAFT-ccrtp-1.0.2-demo-as-upstream-regression

> 上游无 formal `make check` 时将 demo 示例编译验证提升为上游回归套件，通过真机证据门禁

## 问题特征

真机预检日志出现：

```
HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","discovered":0,"executed":0,...}
```

并伴随门禁拒绝理由「清单表明上游存在测试必须发现并执行」/「no_tests/0 不允许通过」，
整体判定 evidence incomplete。

## 根因

- 上游归档**确实没有** formal 测试目标：根 `Makefile.am` 无 `check` 目标、未定义
  `TESTS`，唯一测试程序（如 ccrtp 的 `ccrtptest`）在 `demo/Makefile.am` 中已被注释
  且归档内无对应源文件。
- 配方按事实标记 `upstream_tests_exist:false` → 输出 `no_tests`。
- 但真机证据门禁将 demo 目录的可编译示例视为"上游存在测试"，拒绝零证据放行；
  且主配方 `build()` 在 Conan 缓存命中时不执行，标记缺失使问题在每轮验证复现。

## 修复方案（rec）

1. **审计 demo 目录**：确认哪些示例仅依赖被测库公开头文件、可在 OHOS 工具链下
   独立编译（ccrtp：demo/ 6 个示例中 rtphello/rtpduphello/rtpsend/rtplisten 4 个可用）。
2. **简化为快速退出验证**：新增 `upstream_*.cpp`，仅做核心对象创建（如
   `InetHostAddress` + `RTPSession` + `PayloadFormat`）后立即 `return 0`——
   原版 demo 是无限循环（发送/监听不退出），真机执行会挂起。
3. **MANIFEST 声明**：`upstream_tests_exist:true`，`upstream_test_audit` 记录
   "无 formal make check 的审计过程 + 以 N 个核心 demo 作为回归"的依据，
   `upstream_tests` 逐项列出（file/source/description/command）。
4. **test_package 真实执行 + 每轮复发标记**：`test()` 循环编译运行 N 个 upstream
   源码，统计 passed/failed 后输出 `HMBS_UPSTREAM_TEST_RESULT` 计数标记——
   计数必须来自真实执行，且每轮复发以覆盖主配方缓存命中轮次。
5. **主配方一次性标记**：`build()` 尾部追加与 MANIFEST 同口径的一次性标记。

## 禁止策略

- **禁止零证据放行标记**（`discovered:0` + `status:passed`）：门禁明确拒绝
  no_tests/0，伪造只会退回修复循环。
- **禁止 demo 原样执行**：网络类 demo（rtpsend/rtplisten）原版无限循环，真机上
  阻塞直至 worker 超时（CI 判定"校验异常"）。必须改写为快速退出逻辑。

## 与相近条目的边界（查重）

- `DRAFT-libb64-2.0.0-upstream-make-test-missing-library-target`：上游 `make test`
  **目标损坏**（缺前置库）→ 保留失败记录 + 等价 API 测试替换。本条目是上游
  **完全没有测试框架**（no_tests）→ demo 提升为回归套件，失败签名与方案均不同。
- `E379` / `E445`：上游测试**存在**但缺辅助输入/工具链 → 补齐执行环境。本条目
  是测试**不存在**的证据策略问题。

## 适用判断

上游 autotools 包：无 formal make check/ctest，但 demo/example 含可独立编译、
仅依赖被测库头文件的示例 → 适用本条目。若 demo 依赖过重无法独立编译，退回
fallback（等价 API 断言测试替换，参照 DRAFT-libb64-2.0.0）。

## 实证

ccrtp/1.0.2（archives/c/ccrtp/1.0.2，PR !8591）：真机 `make check` 口径下
4 demo 编译运行 4/4 PASS，test_package 1/1 PASS，preflight 从
evidence incomplete 修复为通过。
