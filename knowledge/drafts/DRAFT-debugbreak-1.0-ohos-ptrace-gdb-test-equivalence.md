# DRAFT-debugbreak-1.0-ohos-ptrace-gdb-test-equivalence

> Contributor: pc4-9 | Status: Draft | Updated: 2026-09-06
> Source: 任务 debugbreak-1.0-r01-pc4-9-20260906T133424Z（debugbreak 1.0 上游测试执行）

## 背景

debugbreak 1.0 上游把测试组织为"测试程序 + .gdb 驱动脚本"：`test/break.gdb`（file break; run）
等，语义为在 gdb 下运行程序并命中断点。实测在 HarmonyOS PC 上全部不可运行：

```text
warning: Could not trace the inferior process.
warning: ptrace: Permission denied
break.gdb:2: Error in sourced command file:
During startup program exited with code 127.
```

C++ 用例（test-debugbreak.gdb）另报 `Undefined command: "import"`（gdb 16.3 无 Python，
`source ../debugbreak-gdb.py` 失败）。

## 根因

HarmonyOS PC 系统限制 ptrace，gdb 无法跟踪子进程（平台安全限制，非库缺陷）；gdb 未启用
Python 属工具链构建配置。但库的机制本身可用：aarch64 上 `debug_break()` 编译为
`.inst 0xd4200000`（brk #0），运行即触发 SIGTRAP——与上游 .gdb 脚本断言的行为完全一致。

## 等价验证方案

1. **进程内信号验证**：安装 SIGTRAP 处理器，调用 `debug_break()`，信号处理函数内 `longjmp`
   返回主流程，断言 `trap_fired==1` → 通过（exit 0）。全程无需 ptrace/gdb。
2. **编译期平台断言**：`#if DEBUG_BREAK_IMPL != DEBUG_BREAK_USE_TRAP_INSTRUCTION
   #error`（仅 `__aarch64__ && !__APPLE__` 生效），证明平台选择逻辑正确。
3. 上游 4 个测试程序直接运行均以 exit=133（128+SIGTRAP）确认陷阱实际触发，作为 gdb 语义的
   直接等价证据。

实现见 `archives/d/debugbreak/1.0/test_package/test_ohos.c`；运行结果：
`PASS: OHOS aarch64 trap-instruction path verified (brk #0 raised SIGTRAP)`（exit 0），
test_package ctest 2/2 通过，W3 .ci-result.json exit_code=0。

## 适用边界

- 适用：断点/陷阱/SIGTRAP/信号类库在 OHOS 的测试执行（无 ptrace 权限场景的等价验证、测试台账中
  将 gdb 阻塞记为真实平台限制并给出恢复条件）。
- 反例：需要调试器语义的用例（如单步、变量检查）无法用进程内信号替代；崩溃定位仍走
  E222/E462（FaultLogger/FP-chain 证据链）。

## 关系

- similar_to: E222（ptrace 不可用时的崩溃证据链）、E462（ptrace blocked 崩溃定位）——
  触发词重叠，但场景（测试执行 vs 崩溃诊断）与方案（进程内功能验证 vs 栈回溯定位）不同；
  本条目补"测试执行"边界。