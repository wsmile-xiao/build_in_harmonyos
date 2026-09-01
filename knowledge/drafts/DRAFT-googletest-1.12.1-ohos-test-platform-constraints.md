# DRAFT-googletest-1.12.1-ohos-test-platform-constraints

> Contributor: junshi_liu | Status: Draft | Updated: 2026-08-31
> Source: GoogleTest 1.12.1 HarmonyOS PC Path B adaptation (PR #7371; migrated from PR #7354, R05-R06)
> 对应 KV: knowledge/drafts/DRAFT-googletest-1.12.1-ohos-test-platform-constraints.kv

## 主题 / 触发场景

OHOS PC (aarch64, clang-only, /tmp 只读沙箱) 上运行 C/C++ 库上游 CTest 测试套件时的
平台约束与逐入口恢复策略。本文以 googletest 1.12.1 的 63 个上游 CTest 入口实测
（35 过 / 28 未通过）为证据，沉淀可复用的 OHOS 测试平台决策矩阵；28 项均属环境/
上游脚本平台约束，不是本库适配缺陷，不得改写为已修复或已通过。

## 现象 / error_signature

上游 CTest 63 个入口实测 35/63 通过、28/63 未通过。可复用错误签名：

```text
Failed to create tmp file /tmp/gtest_captured_stream.XXXXXX
object has no attribute 'assert_'
--gtest_stream_result_to unexpectedly found
mkstemp.*gtest_captured_stream | Read-only file system
```

## 根因 / root_cause（逐分类，含责任归属与恢复条件）

1. **16 项 — `/tmp` 硬编码只读（C++ death-test / 流捕获入口）**
   - googletest `gtest-port.cc:1092` Linux 分支硬编码 `name_template='/tmp/'`
     （仅 iOS 分支读 `TMPDIR`），`mkstemp` 在只读 `/tmp` 失败 → 该类入口在
     `$TMPDIR=$HOME/tmp` 下仍崩溃。
   - 责任归属：环境平台限制（SKILL E002 已知陷阱），非本库适配缺陷。
   - 恢复条件：可写 `/tmp` 的构建环境，或上游 patch 让 Linux 分支也读 `$TMPDIR`；
     不允许改上游断言 / chmod 绕过 / 伪造通过。
2. **11 项 — Python 3.12 移除 `assert_`（Python 驱动测试）**
   - 上游测试脚本为 Python 2 时代写法，Python 3.12 移除
     `unittest.TestCase.assert_` → `AttributeError: object has no attribute 'assert_'`。
   - 责任归属：上游脚本兼容性，非本库配方/源码缺陷。
   - 恢复条件：上游脚本兼容修正（改用 `assertTrue` 等）或 Python 3.12 适配。
3. **1 项 — `gtest_help_test` golden 输出差异**
   - `--help` 输出与上游期望文本不一致（`--gtest_stream_result_to` 等 flag 呈现差异）。
   - 责任归属：上游 golden 文本差异（与 gtest/1.17.0 归档先例同型），非功能缺陷。
   - 恢复条件：环境类，不阻塞本库 PR。

统计口径：16 + 11 + 1 = 28，与 ctest 摘要一致；逐入口命令/cwd/退出码/首条
stdout-stderr/绝对日志/SHA-256 见 R04/R05 任务台账（r04-ctest.log sha256
`0d74d96a…`、r05-ctest.log sha256 `fcda23c8…`）。

## 方案 / rec_approach（可复用 OHOS 平台决策矩阵）

以下策略为围绕该库验证得到的可复用经验，**不是 googletest 已实际采用的修复**；
没有本轮命令/日志证据不表述为修复。

| 场景 | 策略 | 适用边界 |
|------|------|----------|
| 可写临时目录 | 优先 `$TMPDIR=$HOME/tmp` | 仅对尊重 TMPDIR 的入口适用；**硬编码 `/tmp` 的入口 `$TMPDIR` 不适用**，需逐入口确认 |
| HMDFS 软链接 | `rm -f && ln -s`（禁止 `ln -sf` 覆盖） | 需要创建链接时（SKILL E002 系列） |
| 可执行 ELF | 使用框架 `sign-elf` 签名后执行 | 产物含可执行文件时；禁止未签名直接运行 |
| SELinux chmod | 逐入口记录、保留日志 | `chmod` 不生效时按平台限制记录，不伪造通过 |
| clang-only 环境 | 编译器/标志从 Conan Toolchain 或 `self.conf_info` 获取 | 禁止在 recipe build() 裸用 `${CC}`/`${CFLAGS}` 等 shell 变量 |
| 内核裁剪 syscall（`setreuid`/`chroot` 等） | 仅对已实际确认依赖的测试入口做精确 EXCLUDE_LIST | 保留尝试、数量、日志与恢复条件；不宽泛排除 |

## 验证证据 / evidence

- 上游 CTest 63 入口实跑：35/63 通过、28/63 未通过（分类见上）。
- 本库本地门禁：`conan create`（无 `--build=missing`，官方 URL 取源）exit 0；
  test_package/鸿蒙特有测试 3/3 PASS；finish 自然退出码 0（Step5 W3 本地 CI 通过、
  Step7 W5 知识图谱完整性通过、Step9 W2 原子性通过、Step10 submit 就绪全绿）。
- 临时共享知识修复（E219/E253/E305）验证后已按原始 SHA-256 逐字节恢复，
  未纳入 PR。

## 禁止做法

- 修改上游断言 / `sed` 改 gtest-port / 宽泛 EXCLUDE_LIST / 把未运行入口计为通过。
- 把本决策矩阵表述为 googletest 已采用修复（缺少命令/日志证据）。
- 在 draft 阶段创建正式 `E###` 条目、知识索引或独立知识库 PR。
