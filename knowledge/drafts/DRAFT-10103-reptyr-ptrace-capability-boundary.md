# DRAFT-10103-reptyr-ptrace-capability-boundary — OHOS 非特权进程 ptrace/进程内存访问被系统策略整体禁用：ptrace 类工具的适配前能力判定与可用子集

> Contributor: 9C4A | Status: Draft | Updated: 2026-09-27
> Source: reptyr 0.10.0 适配（`feat/reptyr-0.10.0`，平台任务 #10103）
> 证据：真机最小探针（源码 + 原始输出）、上游 2 用例真机执行日志、消费者 18 断言实测
> 配套文件：`knowledge/drafts/DRAFT-10103-reptyr-ptrace-capability-boundary.kv`

## 现象（触发实例：reptyr 0.10.0）

reptyr 0.10.0 在 OHOS PC 上**编译/打包全部通过**（2 个可移植性补丁），但其核心功能在运行期被系统拒绝：
上游 2 个 E2E 用例真机全量执行 **0/2**，两例都停在同一个系统调用上：

```console
# test/basic.py（reptyr -V <pid> 附加）
[+] Checking for problematic process group members...
[+] Making sure we have permission to attach...
Unable to attach to pid 34864: Permission denied

# test/tty-steal.py（reptyr -V -T <pid> 夺取会话）同一 EPERM；
# victim 启动时另见： Unable to PR_SET_PTRACER: Invalid argument
```

而**与 ptrace 无关的可用子集正常**：`reptyr -l` / `-L` 的 pty 创建与子进程 stdio 重定向实测可用，
消费者 18 条断言 18/18 通过（含子进程侧 `REPTYR_PTY` 字符设备校验）。

## 触发条件

- 平台：OHOS / HongMeng Kernel 1.12.0（aarch64，HarmonyOS PC）
- 进程：**非特权用户**（实测 uid=20020085；`CapEff=0x2a`，无 `CAP_SYS_PTRACE`），
  同一 SSH 会话内、同一 UID 的普通进程
- 阶段：runtime（编译期全通，运行期首个 ptrace/process_vm 调用即被拒）

## 能力矩阵（最小探针实测，每场景独立 fork 记录 ret/errno）

| 场景 | 结果 |
|---|---|
| 父→子 `PTRACE_ATTACH` / `PTRACE_SEIZE` | **-1 / EPERM(13)** |
| 兄弟→兄弟（fork 编排）`ATTACH`/`SEIZE` | **-1 / EPERM(13)** |
| 祖父→孙 `ATTACH`/`SEIZE` | **-1 / EPERM(13)** |
| 子进程自行 `PTRACE_TRACEME` | **-1 / EPERM(13)** |
| 父进程 `process_vm_readv(child)` | **-1 / EPERM(13)** |
| `prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY)` | **-1 / EINVAL(22)**（未实现） |
| `cat /proc/sys/kernel/yama/pdebug_scope` | **ENOSYS(38)**（策略接口未向用户态开放） |
| `/proc/self/status` | `Seccomp: 2`（filter）、`Seccomp_filters: 1`、`CapEff: 0x2a`、`NoNewPrivs: 0` |

**判定要点**：不仅是“不能附加他人”，而是**任何关系（含父子）都不能 attach、不能被迫调试（TRACEME）、
跨进程内存读取（process_vm_*）也一并被拒**；调试准入接口（yama/pdebug_scope 类）未开放。

## 根因分析

OHOS 内核/安全域对普通应用进程施加 **seccomp 系统调用过滤 + 调试策略收紧**（样例证据：
`Seccomp: 2/filters:1`、`pdebug_scope` ENOSYS、`CapEff` 无 `CAP_SYS_PTRACE`），
把 ptrace 系与跨进程内存访问整体判为拒绝（EPERM/EINVAL）。
这是**系统安全策略层**的拒绝，**不是**：
- “syscall 未实现”（E051 类：OHOS 对未实现 syscall 常以 **SIGSYS 终止进程**，exit 159）；
- “syscall 存在但参数/权限单点错误”（那会给出 EFAULT/EINVAL/EACCES 等可恢复错误）；
- 本类特征是 **EPERM 于能力入口、进程不崩、用户态无法绕过**（无 LSM 开关/无 sysctl 可写、
  预置 `PR_SET_PTRACER` 亦无效）。

对适配的直接影响：**以 ptrace 为能力前提的工具，其 attach/调试/进程重挂载核心功能在 OHOS 不可提供**；
但**不依赖 ptrace 的子集仍然可用**——需要按“能力面清单”而非“包整体可用/不可用”来判定。

## 解决方案：适配前判定树（可跨库复用）

1. **探针先行（适配前 5 分钟成本）**：编译最小探针（见下），每项独立 fork 记录 ret/errno；
   按 errno 区分三态：
   - `EPERM` → **策略拒绝**（本条目）：核心能力不可用，无用户态绕过；
   - `SIGSYS（signal 31/exit 159）` → syscall 未实现（走 E051/syscall 能力矩阵类处置）；
   - `ENOSYS/EACCES/EFAULT…` → 可捕获并降级（走对应能力/参数类处置）。
2. **盘点“非 ptrace 子集”**：对工具做功能面拆分——
   - attach/调试/重挂载类入口（`reptyr PID`/`-T`/`-s`、`gdb attach`、`strace` 等）：**平台不可用**，
     不得伪造；错误路径应给出清晰诊断（如 reptyr 的 `Unable to attach ... Permission denied`）；
   - 与 ptrace 无关的子集（reptyr `-l/-L` 的 pty 管理、CLI 契约、参数校验等）：**正常提供**，
     作为消费者测试与回归保护对象。
3. **测试台账与申报口径**：上游 attach 入口的 E2E 用例**如实申报平台边界失败**（附 errno 原文与探针证据，
   逐项列技术原因，符合 R51），并以“可用子集消费者测试”补足回归覆盖（R34：真实执行被测二进制）；
   **禁止**通过 `LD_PRELOAD` 替身、桩化 syscall、把失败改写为“跳过/通过”来伪绿。
4. **止损说明**：若工具核心功能**全部**依赖 ptrace 且无可用子集，按平台不可用口径在 notes/test-report
   明确标注（本条目不替代止损决策，只提供判定依据）。
5. **不要做的事**：不要尝试以“预置 `PR_SET_PTRACER`”解除限制（实测 EINVAL，功能未实现）；
   不要依赖 `/proc/sys/kernel/yama/*` 调参（接口 ENOSYS 且无写权限）；不要把 EPERM 误判为“目标进程状态问题”。

## 验证（复现命令）

```bash
# 1) 探针：每场景独立 fork，记录 ret/errno（源码见 reptyr 归档 reports/ptrace-capability-probe.txt）
clang -O0 -o ptrace-probe ptrace-probe.c && ./ptrace-probe
# 期望输出（OHOS aarch64，非特权）：
#   parent->child                PTRACE_ATTACH ret=-1 errno=13 (Permission denied)
#   sibling->sibling             PTRACE_ATTACH ret=-1 errno=13 (Permission denied)
#   grandparent->grandchild      PTRACE_ATTACH ret=-1 errno=13 (Permission denied)
#   child TRACEME                ret=-1 errno=13 (Permission denied)
#   process_vm_readv(child)      ret=-1 errno=13 (Permission denied)
#   PR_SET_PTRACER               ret=-1 errno=22 (Invalid argument)
grep -E 'Seccomp|CapEff' /proc/self/status     # Seccomp: 2; Seccomp_filters: 1; CapEff=0x2a
# 2) 工具侧对照（reptyr 0.10.0）
python3 test/basic.py          # FAIL: Unable to attach to pid N: Permission denied（平台边界）
./reptyr -L sh -c 'echo ok'    # OK: pty 分配 + 子进程 stdio（非 ptrace 子集可用）
```

## 适用范围与边界（与既有条目逐条对照）

- **适用**：所有以 ptrace/process_vm 为能力前提的**可执行工具与库**的适配前能力判定、功能面拆分、
  测试台账与止损口径：进程重挂载（reptyr 类）、调试器 attach（gdb 类）、跟踪器（strace/ltrace 类）、
  ptrace 型沙箱/模拟器、调试库 attach 模式等。
- **不适用/边界**：
  - 崩溃诊断的替代证据链 → **E222**（FaultLogger/符号化证据链）、**E462**（SIGSEGV handler + FP-chain），
    二者面向“ptrace 不可用时如何定位崩溃”；本条面向“能力边界本身 + 适配前判定 + 可用子集 +
    测试台账口径”，不涉及崩溃诊断方法；
  - 断点/陷阱类库的**测试等价执行**（进程内信号代替 gdb）→ `DRAFT-debugbreak-1.0-ohos-ptrace-gdb-test-equivalence`；
    本条的结论恰恰相反：attach 类工具的**功能面**没有进程内替代，只能标注不可用（两者互补，不重叠）；
  - 运行期能力探测+优雅降级方法论 → `DRAFT-10686-skypat-perf-events-runtime-capability-probe`（perf，EACCES）、
    `DRAFT-ohos-syscall-capability-matrix-fork-probe`（未实现 syscall，SIGSYS，逐项 fork 探测法）：
    本条复用“独立 fork 逐项探测”方法，但对象（ptrace 权限面）、errno 语义（EPERM=策略拒绝≠未实现）、
    结论（无降级可用面）不同；
  - seccomp/未实现 syscall 的 SIGSYS 线 → **E246**、**E051**；本条 syscall 存在但被策略拒绝（EPERM，进程不崩）。

## 关联条目

- similar_to: E462、E222、E051、E246
- 触发实例归档：`archives/r/reptyr/0.10.0/`（`reports/ptrace-capability-probe.txt`、`reports/upstream-*.log`、
  `reports/test-report.md`、`test_package/test_reptyr.sh`）
