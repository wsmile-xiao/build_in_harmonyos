# E327 - 旧式 Bash 测试框架不得把准备失败报告为通过

## 错误特征

这类问题不是单一的 `/tmp` 不可写或 `/bin/bash` 缺失，而是测试框架在这些准备
错误之后仍返回 0。典型日志如下：

```text
cp: /tmp/iasl-...: Read-only file system
cp: /tmp/acpiexec-...: Read-only file system
iasl compiler not found
exit_code=0
```

修复第一层后还可能出现第二层假绿：

```text
xargs: Unknown option 'I'
64-bit nopt mode:
    PASS       :
    FAIL       :
    Tests      :
exit_code=0
```

此时没有用例被执行，不能把顶层返回码 0 解释为上游测试通过。

## 触发条件

- 上游测试由多层 Bash 脚本组成，顶层脚本和子脚本依赖固定 shebang。
- runner 把工具复制到硬编码 `/tmp`，但目标系统仅允许任务私有目录写入。
- 子脚本使用 GNU `xargs -I/-P` 等目标 Toybox 不支持的组合。
- 准备分支使用裸 `exit`，或函数/子进程返回值未传递到顶层。
- CI 只检查进程退出码，不检查执行数量、结构化 Summary 或正向产物。

## 根因分析

E002 已说明 OHOS `/tmp` 只读，应设置可写 `TMPDIR`；E201 已说明标准
`/bin/bash` 和部分测试工具在 OHOS 上不可用。但单独应用这两条知识仍可能留下
假绿：上游脚本在复制、解释器调度或 `xargs` 失败后继续执行，最终创建一个
PASS/FAIL/Tests 全为空的 Summary 并返回 0。

本草稿新增的知识是测试结果的可信边界：准备阶段必须 fail fast，所有跨脚本阶段
必须传递状态，并且成功必须同时满足“非空结构化结果 + 正向产物”。

## 解决方案

1. 使用任务私有目录设置 `TMPDIR`，并在复制工具前验证目录可创建、可写。
2. 把 Bash 声明为 Conan `tool_requires`，顶层脚本由该 Bash 启动。
3. 子脚本通过当前 `$BASH` 显式调度，不创建 `/bin/bash` 软链接，不修改系统镜像。
4. 纯目录创建使用 `mkdir -p`，不依赖可能被目标执行策略拒绝的 `install -d`。
5. 对迁移子集使用顺序循环，避免依赖目标 `xargs` 的 GNU 扩展，并在当前 shell
   中累积用例状态。
6. 所有 setup、copy、compile、execute 阶段使用显式非零退出码并逐层检查。
7. 在配方中解析本次最新 Summary，要求目标 mode 的 PASS、FAIL、Tests 都是数字，
   且 `PASS > 0`、`FAIL == 0`、`Tests > 0`；同时要求目标 AML 产物存在。
8. 如果跳过与所选集合无关的前置阶段，必须使用显式开关并在报告中声明，不能把
   该阶段或完整测试资产计入通过数。

## acpica-unix 对照证据

| 阶段 | runner | 结果 |
|---|---|---|
| 原始上游脚本 | `codex-acpica-unix-issue-2207-aslts-baseline-20260815-223846-37405` | `/tmp` 三次复制失败、`iasl compiler not found`，但 rc=0 |
| 仅修 TMPDIR/fail-fast | `...aslts-patched-20260815-225949-48211` | rc=1，证明错误不再被吞；同时暴露错误工作目录 |
| 正确目录、首轮子集 | `...aslts-constant-n64-v2-20260815-231514-53840` | rc=0，但 `xargs -I` 失败且 Summary 为空，判定仍是假绿 |
| 最终迁移子集 | `...aslts-constant-n64-v4-20260815-232510-57982` | rc=0；Summary `PASS=1, FAIL=0, Tests=1`；`constant.aml` 18,522 字节 |
| 完整 shadow 首轮 | `codex-acpica-unix-issue-2207-shadow-bclass-20260815-233817-4051` | `install -d` 被拒绝；配方因无 AML 明确失败，证明正向产物门禁有效 |
| 完整 shadow 修复 | `codex-acpica-unix-issue-2207-shadow-bclass-r2-20260815-234914-11351` | `total_asl=1291`；`PASS=1, FAIL=0, Tests=1`；L0/L1/L2/L4/L5/L1e 通过 |

最终单用例日志同时包含：

```text
ASLTS: START, constant 64-bit nopt mode
ASLTS: FINISH, constant 64-bit nopt mode, SUCCESS
```

## 覆盖边界

官方 `acpitests-unix-20260408` 资产包含 1,291 个 `.asl` 文件。本次只选择
`functional/constant` 目录的 4 个源文件、`n64` 模式，最终执行 1 个逻辑测试，
并另行保留 DSDT 模板和 Conan `test_package` 往返验证。未运行的模板、集合和模式
不计为通过，不声称 ASLTS 全量通过。

## 去重与扩展关系

- `E002`：提供可写 `TMPDIR` 的基础方案；本草稿补充准备失败的状态传播和正向证据。
- `E201`：覆盖 `/bin/bash` 不存在；本草稿补充 Conan Bash 的传递式显式调度。
- `E253`：强调上游测试入口迁移和如实报告覆盖率；本草稿给出空 Summary 假绿的
  可执行判定规则。
