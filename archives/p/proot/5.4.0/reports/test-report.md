# proot 5.4.0 测试报告
<!-- 放置路径: archives/p/proot/5.4.0/reports/test-report.md -->

> **项目**: proot 5.4.0
> **测试日期**: 2026-10-12
> **测试环境**: HarmonyOS HongMeng Kernel 1.12.0 aarch64（HAD-W32/W24，HDC 报告 API 23）
> **测试类型**: 官方测试套件（`make -C test check`）+ 消费侧回归（`test_package/test_proot.sh`）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游套件总检查数 | 134 | 100% |
| 通过 (PASS) | 2 | 1.5% |
| 失败 (FAIL) | 110 | 82.1% |
| 跳过 (SKIP) | 22 | 16.4% |
| 消费侧断言（test_package） | 16 | **16/16 PASS** |

**上游套件通过率**: 2/134 —— 其中 2 项"通过"均为**断言「非 root 使用 -i/-0 必须失败」**的
反向用例，因平台边界确实失败而按断言口径通过（与上游预期原因不同，见 3.1）。
**消费侧回归**: 16/16 PASS（`conan create` 内 `test_proot.sh` 真实执行，覆盖 CLI 全部可用面）。

---

## 二、测试结论

### 2.1 总体评价

⚠️ **适配本身完成且可复现构建**；但 proot 的**隔离执行核心功能在 OHOS 上不可用**——
这是内核策略（对非特权进程禁用 ptrace）导致的能力边界，与适配质量无关，任何用户态
补丁都无法绕过。CLI 表面（版本/帮助/参数校验/错误报告）完整可用并经消费测试验证。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| OHOS 禁止非特权 ptrace（PTRACE_TRACEME/ATTACH/SEIZE 全被拒） | 全部 tracee 执行路径（110/134 项失败） | 🔴 平台边界（不可修复） |
| 上游套件部分用例依赖缺失外部工具（gdb/strace/ldd/setcap/domainname/docker/CARE） | 22/134 项按上游惯例跳过（exit 125） | 🟢 环境限制（上游语义） |
| `test-gdb-ptrace.sh` 前置程序在无 ptrace 环境挂死 | 1 项（120s 看门狗击杀后记 FAILED） | 🟡 平台边界衍生 |

### 2.3 可用功能清单

```
✅ 版本/帮助: proot --version / -V / --help 退出码与输出完整（含加速器检测行）
✅ 参数校验: 缺命令/未知选项/不可用 rootfs 的报错与退出码
✅ rootfs 绑定校验: 不可用 rootfs 在创建 tracee 前即被拒（"can't sanitize binding"）
❌ 隔离执行: proot <命令> 在 ptrace(TRACEME) 被内核拒绝（EACCES），无法运行任何 guest 程序
❌ 扩展功能: -b/-0/-R/-S/-p/-n 等均以 tracee 为前提，同不可用
```

### 2.4 已知限制

1. **OHOS 内核对非特权进程禁用 ptrace**（Seccomp filter 生效、无 CAP_SYS_PTRACE；
   TRACEME/ATTACH/SEIZE/process_vm_readv 全部被拒），proot 的核心机制不可用。
2. 上游套件中依赖 gdb/strace/ldd/setcap/domainname/docker 与 CARE 的用例在本环境按
   上游惯例跳过（`exit 125`）。
3. 若上游用例将来需要在该平台运行，需要平台开放 ptrace 或提供能力豁免——非本包能解决。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 | 说明 |
|--------|------|------|------|
| `check-test-82ba4ba1.c` | 断言 `proot -i 123:456`（非 root）**必须失败** | ✅ PASS | 因平台边界失败而满足反向断言；实际原因与上游预期不同（如实记录） |
| `check-test-c5a7a0f0.c` | 同上（`! proot -i 123:456` 反向断言） | ✅ PASS | 同上 |

> 除上述 2 项反向用例外，其余 110 项均以 `PTRACE_TRACEME` 被拒告终（样本见四）。

### 3.2 失败的测试（110 项，按主因归类）

| 类别 | 数量 | 代表样本 | 说明 |
|------|------|----------|------|
| tracee 执行在 `ptrace(TRACEME)` 被拒（EACCES） | 109 | `test-00000000.sh`、`check-test-<*.c>` 各用例 | 平台能力边界主因；每个用例的真实 proot 输出均为 `proot error: ptrace(TRACEME): Permission denied` |
| 前置程序在无 ptrace 环境挂死（看门狗击杀） | 1 | `test-gdb-ptrace.sh`（前置 `gdb-ptrace-test`） | 120s 无输出被监督器击杀，按 FAILED 记录 |

> 另有少数脚本自身写入只读 `/tmp`（如 `test-0228fbe7.sh`），属环境因素叠加；不影响
> "全部失败均系平台边界"的结论（proot 在更早的 TRACEME 处即失败）。

### 3.3 跳过的测试（22 项，按上游守卫语义归类）

| 类别 | 数量 | 用例 |
|------|------|------|
| CARE 工具未构建（本包只构建 proot） | 6 | `test-careauth`、`test-careexit`、`test-carehwcp`、`test-carequot`、`test-c68d18dc`、`test-proocare`（另依赖 /boot） |
| 缺失外部工具 | 6 | gdb：`test-2db65cd2`；strace：`test-df4de4db`、`test-fbca9cc2`；ldd：`test-8a83376a`；setcap：`test-e87ca6ca`；domainname：`test-5996858d` |
| docker/podman 缺失 | 1 | `test-docker` |
| 需要 root（`id -u` == 0） | 1 | `test-d1be631a` |
| 前置测试程序不存在/未编译出（`-static` 等） | 4 | `test-ptrace-exec-trap`（缺 `ptrace-3`）、`test-5bed7143`（×2）、`test-kkkkkkkk` |
| 用例自身前置条件不满足（上游语义） | 4 | `test-230f47ch`、`test-dddddddd`、`test-hhhhhhhh`、`test-9f5eeb72` |

---

## 四、关键问题分析

### 问题1: OHOS 禁止非特权进程使用 ptrace（本任务核心事实）

**现象**：

```text
$ proot -r / /bin/true
proot error: ptrace(TRACEME): Permission denied
proot error: execve("/bin/true"): Permission denied
...
proot 退出码 = 1
```

自建最小探针（同一 SSH 会话、同一 UID）实测：

```text
child PTRACE_TRACEME                       exit=1 (refused)
parent PTRACE_ATTACH child                 rc=-1 errno=13 (Permission denied)
parent PTRACE_SEIZE child                  rc=-1 errno=13 (Permission denied)
process_vm_readv(child)                    rc=-1 errno=13 (Permission denied)
prctl(PR_SET_PTRACER, PTRACER_ANY)         rc=-1 errno=22 (Invalid argument)
CapEff:	000000000000002a                  （无 CAP_SYS_PTRACE）
Seccomp:	2                          （Seccomp filter 模式生效）
Seccomp_filters:	1
yama ptrace_scope: open errno=2 (No such file or directory)
```

**根因分析**：OHOS 内核对非特权进程施加 seccomp filter 并在系统策略层拒绝 ptrace 及
进程内存访问；进程能力集不含 `CAP_SYS_PTRACE`。proot 的每次 tracee 启动都以
`PTRACE_TRACEME` 为必经之路，因此全部隔离执行路径在第一步即失败。

**解决方案**：平台边界，**不可在应用层绕过**（与同平台 reptyr 任务记录一致）。本包
以如下方式如实交付与留证：
1. 上游测试 134 项真机全量执行、逐项归类（本文档 §三）；
2. 消费侧 `test_package/test_proot.sh` 16 条断言覆盖平台可用面（版本/帮助/参数校验/
   平台策略一致性），并在 `conan create` 中真实通过；
3. 复现探针与总输出在本任务工作区留档（`ptrace-capability-probe.txt`）。

### 问题2: 上游测试依赖缺失与挂死

**现象**：22 项因缺工具/CARE 按上游守卫跳过（`exit 125`）；`test-gdb-ptrace.sh` 的
前置程序 `gdb-ptrace-test`（自身用 ptrace 模拟 gdb）在无 ptrace 环境无输出挂死。

**根因分析**：环境工具集（gdb/strace/ldd/setcap/domainname/docker）与 CARE 未提供；
挂死源于同一 ptrace 边界（程序阻塞在等待永不发生的事件）。

**解决方案**：执行时以监督器保持 `make -C test check` 逐项语义不变，仅对运行超过
120s 的**叶子进程**实施看门狗击杀，使套件可以完整走完（击杀 1 次，如实记 FAILED）。

---

## 五、测试环境

```text
proot 5.4.0（upstream tarball codeload v5.4.0，sha256 29248aac…a5f68）
OHOS SDK clang 15.0.4（native/llvm/bin），talloc/2.4.4（Conan 制品仓）
Conan profile: ohos-aarch64-device（本机）；CI 使用仓库 profile
设备: HarmonyOS PC（HongMeng Kernel 1.12.0，aarch64，HAD-W32/W24）

上游套件命令: make -C test check CC=<OHOS SDK clang>
              （94 个 .sh + 36 个 .c 文件 → 134 项检查；监督器逐项记录）
套件结果: 2 ok / 110 FAILED / 22 skipped / 1 次看门狗击杀（完整清单见工作区 upstream-test3.log）
消费测试: conan create 内 sh test_proot.sh → 16/16 PASS（conan-create.log："# passed: 16, failed: 0"）
配方门禁: conan-verify（profile ohos-aarch64-device）G0–G4 + L2/L4/L5 全 PASS；
          G2 conan create 成功（reports/conan-verify-report.md、reports/conan-create.log）
本地 CI 门禁: L0/L1/L1a/L1b/L1e/L2/L4/L5 PASS（reports/w3-local-ci.log）；
          finish 写入 .ci-result.json（exit_code=0）
```

> 原始日志（`upstream-test3.log`、代表性用例日志、探针输出、`conan-create.log`）保存在
> 本任务工作区；平台 CI 构建编号在 CI 通过后补记。

---

*报告生成时间: 2026-10-12*
