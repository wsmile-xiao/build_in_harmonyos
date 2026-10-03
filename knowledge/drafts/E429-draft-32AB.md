# HarmonyOS 6.0 aarch64 上 pty 的 TIOCSTI 输入注入返回 EACCES

Status: DRAFT

Source: finalcut 0.9.1，HarmonyOS PC 6.0 aarch64 真机测试

PR: `feat/finalcut-0.9.1`（待创建）

## 相关既有条目

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| `DRAFT-rungetty-1.2-tcflsh-eacces-on-owned-pty-slave` | 自有 pty 上 `TCFLSH`/`tcflush()` 返回 EACCES；强调每个 ioctl 应单独探测 | 本草稿针对 `TIOCSTI` 输入注入及依赖该操作的测试注册；不同 ioctl、不同语义，不能将 TCFLSH 结论直接套用 |
| `DRAFT-10861-splitvt-1.6.6-tioccsctty-needs-session-leader` | `TIOCSCTTY` 对会话首进程身份的要求 | 本草稿不涉及控制终端接管或 `setsid()`，而是普通进程调用 `TIOCSTI` 的权限拒绝 |
| `DRAFT-E429-cfm-termios-tui-pty-consumer-test` | 无 CLI 模式的 TUI 消费者需要通过 pty 检查渲染输出 | 本草稿补充 pty 输入注入 ioctl 的平台能力边界与精确跳过范围；该条不覆盖 TIOCSTI/EACCES |

查重检索了 `knowledge/graph/index.tsv`、`knowledge/doc/` 与 `knowledge/drafts/` 中的 `TIOCSTI`、`TIOCSTI.*EACCES`、`keyboard injection`。正式索引/文档没有同一 errno 与 ioctl 的行为条目；draft 中上述条目只涉及相邻但不同的 ioctl 或 PTY 测试方法。原分支上的 finalcut 测试草稿是同包历史草稿，将由本次更准确、以真机错误为依据的配对草稿替换。

## Scope

实测范围限定为 HarmonyOS 6.0 aarch64 真机上、当前 HNP 测试进程凭据下、进程自己创建的 pty slave。其它 HarmonyOS 版本、设备安全策略或权限上下文需要重新探测。

## Symptom

在设备上运行：

```text
python3 -c 'import pty,fcntl; m,s=pty.openpty(); fcntl.ioctl(s,0x5412,bytes([120]))'
```

得到真实错误：

```text
PermissionError: [Errno 13] Permission denied
```

`finalcut 0.9.1` 的 `fkeyboard_test` 有 13 个 CppUnit 用例，其中 9 个使用 `TIOCSTI` 把模拟按键注入终端输入队列；剩下 4 个用例不依赖注入。真机拒绝 ioctl 后，适配只阻止那 9 个用例注册，仍运行剩余用例。

## Root Cause

目标系统在本次测试进程调用 pty slave 的 `TIOCSTI` 输入注入边界返回 `EACCES(13)`，Python 的 `fcntl.ioctl` 将 errno 映射成 `PermissionError`。证据说明该测试上下文无法使用此能力；它不能单独证明所有 HarmonyOS 版本均拒绝，也不能推出所有终端 ioctl 均受限。

## Recommended Fix / Workaround

在实际目标设备上探测 `TIOCSTI`。仅当探针确认能力不可用时，跳过明确依赖注入的用例；保留非注入用例，并将跳过数和 errno 记录为平台限制。对需要跨不同 HarmonyOS 策略运行的单个测试二进制，优先使用运行时能力探测决定测试注册。

此处的 9 个排除用例是上游 `fkeyboard_test` 的测试模拟机制，不是 FINAL CUT 生产功能；不应因测试 ioctl 受限而改写生产键盘输入路径。

## Fallback

如果测试框架不能动态注册，可在狭窄的平台条件中门控仅依赖 `TIOCSTI` 的测试函数。不要禁用整个 keyboard suite；同一目标的另外 4 个独立测试仍应运行。

## Forbidden Approaches

- 不要以 `sudo`、能力位或更改系统权限来制造通过结果；这会改变被测上下文，并掩盖实际普通进程能力。
- 不要将所有终端测试或生产输入代码一并禁用。
- 不要把本条结论套用于 `TCFLSH`、`TIOCSCTTY` 等不同 ioctl。

## Verification

在目标 HarmonyOS 设备上复算探针：

```bash
python3 -c 'import pty,fcntl; m,s=pty.openpty(); fcntl.ioctl(s,0x5412,bytes([120]))'
```

本任务已在设备上复现 `PermissionError: [Errno 13] Permission denied`。同一设备上适配后的 `make -j1 check` 运行 28 个适用上游目标，28/28 通过；BSD 专属的两个目标不适用。`fkeyboard_test` 中 4 个非注入用例运行通过，9 个注入用例不注册。原始探针输出见 `archives/f/finalcut/0.9.1/reports/tiocsti-probe.md`，逐项测试结果见 `reports/upstream-tests-ledger.md`。

## Prevention

终端键盘测试在首次依赖合成输入时记录所用 ioctl，并在目标环境确认能力。按测试用例最小范围分类 PASS/N/A，不能把未注册或未执行当成通过。

## References

- `archives/f/finalcut/0.9.1/patches/0006-upstream-test-portability.patch`
- `archives/f/finalcut/0.9.1/reports/tiocsti-probe.md`
- [FINAL CUT 0.9.1 上游键盘测试](https://github.com/gansm/finalcut/blob/0.9.1/test/fkeyboard-test.cpp)
