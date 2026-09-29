# 测试报告 — reptyr 0.10.0（HarmonyOS PC / aarch64）

> **项目**: reptyr 0.10.0（https://github.com/nelhage/reptyr）
> **测试日期**: 2026-09-27
> **测试环境**: HarmonyOS PC，HongMeng Kernel 1.12.0 aarch64（HAD-W32），OHOS SDK clang 15.0.4
> **测试类型**: 上游测试真机全量执行（2 用例，0 通过，2 失败——平台 ptrace 边界）+ 消费者功能测试（test_package，18 条断言）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试总数 | 2 | — |
| 上游通过 (PASS) | 0 | 0% |
| 上游失败 (FAIL) | 2 | 100%（平台边界，非适配缺陷，见 §四） |
| 适配新增测试总数 | 18 | 100% |
| 新增通过 (PASS) | 18 | 100% |
| 新增失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**消费者断言通过率**: ✅ **100%（18/18）**

> 上游 reptyr 0.10.0 共 2 个测试程序（`test/basic.py`、`test/tty-steal.py`，pexpect 驱动），
> 均以 `PTRACE_ATTACH` 为入口。本机实测：**OHOS 内核对非特权进程禁用 ptrace**——
> 父→子、兄弟→兄弟、祖父→孙的 ATTACH/SEIZE 全部 `EPERM`，`PTRACE_TRACEME` 与
> `process_vm_readv` 同样 `EPERM`；`PR_SET_PTRACER` 返回 `EINVAL`（未实现）。
> 探针源码与原始输出见 `reports/ptrace-capability-probe.txt`。这是被测工具核心机制的
> 系统级策略边界，任何用户态适配都无法改变；两个用例的失败已如实申报（R51）。

---

## 二、测试结论

### 2.1 总体评价

⚠️ **有条件通过**。包可构建、可安装；**pty 管理功能（`-l` / `-L`）与全部 CLI 行为真实可用**
（18/18 消费者断言，含 CI L1e 破坏性反向验证）；**ptrace 附加功能（`PID` / `-T` / `-s`）被
OHOS 系统策略禁止**——上游 2 个 E2E 用例因此在该平台无法通过，属环境能力边界，与适配质量无关。
适配补丁只有 2 个可移植性修复（平台识别、头文件冲突），无平台宏、无 stub、无行为削减。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| OHOS 禁止非特权进程 ptrace（EPERM；进程 Seccomp 过滤） | `reptyr PID` / `-T` / `-s` 全部不可用；上游 2 用例失败 | 🔴（平台边界，无法通过适配消除） |
| 上游 2 个 E2E 用例依赖 ptrace | 上游通过率 0/2 | 🟡（已如实申报，消费者测试补足可用面） |

### 2.3 可用功能清单

```
✅ reptyr -v / -h                版本与用法输出（rc=0）
✅ 参数校验                       缺 pid / 非数字 pid / 未知选项（rc=1 + 报错）
✅ 附加错误报告                   不存在的 pid 报 No such process（rc=1）
✅ reptyr -l                     新建 pty 对并播报 slave（/dev/pts/N）
✅ reptyr -L CMD                 在新建 pty slave 上运行命令、导出 REPTYR_PTY、
                                 转发子进程 stdout；slave 为字符设备
❌ reptyr PID / -T / -s          需要 PTRACE_ATTACH —— OHOS 非特权进程 EPERM
```

### 2.4 已知限制

1. **ptrace 被系统策略禁止**（核心限制）：在任何使用 reptyr 附加功能前会被拒；
   错误提示为 `Unable to attach to pid N: Permission denied`。探测/复现：
   `reports/ptrace-capability-probe.txt`。
2. 上游测试需要真实终端与 pexpect；本机以私有 `--target` 安装 pexpect 4.9.0 执行
   （未污染共享 venv）。`python-prctl` 在 OHOS 不可用，但 tty-steal.py 对 prctl 分支
   有优雅降级（打印提示后继续），不是失败根因。
3. `reptyr -l` 在 stdin 为 EOF（如 `</dev/null`）时会忙等（上游未处理 `read()==0`）；
   自动化脚本中应带看护超时（见 test_package 中的 kill 收尾）。

---

## 三、测试详情

### 3.1 上游测试（真机全量执行，2 用例）

| # | 用例 | 命令 | 结果 | 技术原因（逐项） |
|---|------|------|------|------------------|
| 1 | basic.py：`reptyr -V <pid>` 把 victim 重挂到新 pty 后继续交互 | `python3 test/basic.py` | ❌ FAIL | preflight `PTRACE_ATTACH` 返回 EPERM；日志原文 `Unable to attach to pid <N>: Permission denied`（reports/upstream-basic.log） |
| 2 | tty-steal.py：`reptyr -V -T <pid>` 夺取整个终端会话 | `python3 test/tty-steal.py` | ❌ FAIL | 同一 EPERM（reports/upstream-tty-steal.log）；victim 程序的 `PR_SET_PTRACER` 返回 `Invalid argument`，证据见 reports/upstream-basic.log 与 reports/ptrace-capability-probe.txt |

> 说明：两用例均已完成"可运行环境实际运行"，失败发生在被测工具调用内核能力的**首个系统调用**处，
> 与补丁/配方无关（未打补丁的同一份代码在 Linux 上即为此设计的通过路径）。

### 3.2 消费者测试（test_package/test_reptyr.sh，18/18 PASS）

| # | 测试项 | 结果 |
|---|--------|------|
| 1 | reptyr 二进制已安装并在 PATH 上 | ✅ PASS |
| 2 | `reptyr -v` 退出码 0 | ✅ PASS |
| 3 | `-v` 输出 "This is reptyr version 0.10.0" | ✅ PASS |
| 4 | `reptyr -h` 退出码 0 | ✅ PASS |
| 5 | `-h` 输出包含 `reptyr [-s] PID` 用法 | ✅ PASS |
| 6 | 缺 pid 退出码 1 | ✅ PASS |
| 7 | 缺 pid 报 "No pid specified to attach" | ✅ PASS |
| 8 | 非数字 pid 退出码 1 | ✅ PASS |
| 9 | 非数字 pid 报 "Invalid pid: must be integer" | ✅ PASS |
| 10 | 不存在的 pid 退出码 1 | ✅ PASS |
| 11 | 不存在 pid 报 "No such process" | ✅ PASS |
| 12 | 未知选项 `-Z` 退出码 1 | ✅ PASS |
| 13 | 未知选项打印 Usage | ✅ PASS |
| 14 | `reptyr -l` 播报新建 pty slave（/dev/pts/N） | ✅ PASS |
| 15 | `reptyr -L` 播报新建 pty slave | ✅ PASS |
| 16 | `-L` 转发子进程 stdout（child-marker-42） | ✅ PASS |
| 17 | 子进程侧确认 REPTYR_PTY 为字符设备 | ✅ PASS |
| 18 | REPTYR_PTY 与播报的 slave 路径一致 | ✅ PASS |

### 3.3 失败的测试

无（消费者）；上游 2 用例失败原因见 §3.1 与 §四。

### 3.4 跳过的测试

无。`matrix.sh` 是 32/64 位构建矩阵脚本（仍以 make test 为入口），不属于额外用例。

---

## 四、关键问题分析（平台边界）

### 问题: OHOS 禁止非特权进程使用 ptrace

**现象**：上游 2 个 E2E 用例在 `ptrace(PTRACE_ATTACH, pid, ...)` 处返回 `-1 / EPERM`；
`reptyr` 输出 `Unable to attach to pid N: Permission denied`。

**最小探针（同一会话、同一 UID，源码+输出见 `reports/ptrace-capability-probe.txt`）**：

```
父→子 ATTACH/SEIZE                -> EPERM
兄弟→兄弟 ATTACH/SEIZE            -> EPERM
祖父→孙 ATTACH/SEIZE              -> EPERM
PTRACE_TRACEME                    -> EPERM
process_vm_readv                  -> EPERM
prctl(PR_SET_PTRACER, -1)         -> EINVAL
/proc/sys/kernel/yama/pdebug_scope -> 读取 ENOSYS
进程状态: Seccomp=2 (filter), Seccomp_filters=1, CapEff=0x2a (无 CAP_SYS_PTRACE)
```

**根因分析**：OHOS 内核对应用进程施加 seccomp 系统调用过滤并收紧 ptrace 权限模型
（附带名为 `yama/pdebug_scope` 的调试策略接口，未向用户态开放）。非特权进程既不能附加
任何目标（包括自己的子进程），也不能被调试器附加。

**解决方案（止损口径）**：用户态无法解决——不伪造、不打桩、不弱化断言。处置：
1. 上游测试如实申报 0/2 + 逐项技术原因（R51）；
2. `test_package` 覆盖平台**可用**行为面（pty 分配、参数校验、错误报告）共 18 条断言；
3. 探测方法与边界写入 `reports/ptrace-capability-probe.txt` 与 notes.md，供同类
   ptrace 工具（debugger/tracer）的适配提前判定。

---

## 五、测试环境

```
OS:        HarmonyOS PC / HongMeng Kernel 1.12.0 aarch64 (HAD-W32)
Compiler:  OHOS SDK clang 15.0.4 (aarch64-linux-ohos)
Conan:     2.29.1 (OHOS-adapted)
Profile:   ohos-aarch64-device
Source:    reptyr-0.10.0.tar.gz（codeload.github.com 官方端点；sha256 c6ffbc34a511ac00d072219bda30699e51f2f4eb483cbae9e32e981d49e8b380）
Artifacts: bin/reptyr; share/man/man1/reptyr.1; share/man/fr/man1/reptyr.1;
           share/bash-completion/completions/reptyr.bash
测试依赖:  pexpect 4.9.0（私有 --target 安装执行上游套件）
```

**验证链路**（全部在本机实测）：
- 手工构建：`make` rc=0；`./reptyr -v` 输出 "This is reptyr version 0.10.0."
- 上游测试：2/2 完成执行（0 通过、2 失败——EPERM 平台边界）
- `conan create`（clean）日志内 test_package：`# passed: 18, failed: 0`
- `conan-verify`：G0–G4 + L2/L4/L5（见 reports/conan-verify-report.md）
- 本地 CI 门禁：见 reports/w3-local-ci.log

---

*报告生成时间: 2026-09-27*
