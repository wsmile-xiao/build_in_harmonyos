# jattach 2.2 测试报告

> **项目**: jattach 2.2
> **测试日期**: 2026-09-20
> **测试环境**: HarmonyOS 6.1.0 (HongMeng Kernel 1.12.0 aarch64, HAD-W32/W24)
> **测试类型**: 消费者测试（`test_package/`，上游无测试套件）+ 手动功能验证
> **编译工具链**: OHOS SDK clang 15.0.4（aarch64-linux-ohos），Conan 2.29.1

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 18 | 100% |
| 通过 (PASS) | 18 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

> 上游测试套件: **N=0**。上游 2.2 tag tarball 无 tests/ 目录，Makefile 无
> `check`/`test` 目标（`make -n check` → `No rule to make target 'check'`）。
> 因此以上 18 项为适配补全的鸿蒙消费者测试（R51）。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。jattach 2.2 在 HarmonyOS PC（aarch64）上零源码修改编译成功；
CLI 契约、`/proc` 进程查找、HotSpot attach 触发路径（触发文件 + SIGQUIT）与
AArch64 ELF 产物校验全部实机通过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| AF_UNIX 路径 socket 创建被 HMMAC 拒绝 | JVM 侧 attach socket 正路径无法在设备 shell 会话复现 | 🟡（平台限制，见 E461） |
| SysV 信号量被 seccomp 以 SIGSYS 终止 | OpenJ9 attach 路径不可用（本平台无 JVM，实际不可达） | 🟡（平台限制，见 E246） |
| `/tmp` 为只读 erofs | 默认 tmp 路径不可写，需 `JATTACH_PATH` 重定向 | 🟢（见 E002，工具已提供环境变量） |

### 2.3 可用功能清单

```
✅ `jattach`（无参数）: 用法/版本横幅，exit 1
✅ PID 校验: 非数字/0 → "is not a valid process ID"，exit 1
✅ 进程查找: /proc/<pid>/status 解析，缺失进程 → "Process N not found"，exit 1
✅ HotSpot attach 触发: 目标 cwd（或 JATTACH_PATH）下创建 .attach_pid<PID>，
   向目标发送 SIGQUIT，等待 attach socket，失败时报错并清理触发文件
✅ 产物格式: aarch64 musl PIE ELF
⚠️ HotSpot 正路径（Connected to remote JVM → JVM response code）: 需目标 JVM
   自行创建 /tmp/.java_pid<PID>（或 JATTACH_PATH 下）socket，本机无法模拟（E461）
❌ OpenJ9 路径: semget/semop 被 seccomp SIGSYS 终止，平台不可用（E246）
```

### 2.4 已知限制

1. **attach 正路径无法本机复现**：HarmonyOS HMMAC 对非应用进程拒绝 AF_UNIX
   路径 socket 的 `bind()`（`EPERM`；abstract socket 与 socketpair 可用）。
   attach socket 由目标 JVM 创建，jattach 只做 `connect()`；设备 shell 会话
   无法搭建模拟 JVM 监听端，故未实测 socket 往返。
2. **OpenJ9 路径不可用**：`semget/semop` 触发 SIGSYS（core dump）。HarmonyOS
   当前无 JVM 运行环境，该分支实际不可达；HotSpot 为主路径且相关逻辑均已验证。
3. `/tmp` 只读，运行场景需 `JATTACH_PATH` 指定可写目录（上游原生支持）。

---

## 三、测试详情

### 3.1 通过的测试（`test_package/test_jattach.sh`，18/18）

| # | 测试项 | 功能 | 结果 |
|---|--------|------|------|
| 1 | binary installed and executable | 安装产物可执行 | ✅ PASS |
| 2 | no-argument invocation exits 1 | 无参数退出码 | ✅ PASS |
| 3 | version banner printed | 版本横幅（jattach 2.2） | ✅ PASS |
| 4 | usage line printed | 用法行 | ✅ PASS |
| 5 | all 10 documented commands listed | 10 个子命令文档完整 | ✅ PASS |
| 6 | non-numeric PID rejected (rc) | `abc` → exit 1 | ✅ PASS |
| 7 | non-numeric PID diagnostic | 错误信息 | ✅ PASS |
| 8 | PID 0 rejected (rc) | `0` → exit 1 | ✅ PASS |
| 9 | PID 0 diagnostic | 错误信息 | ✅ PASS |
| 10 | missing process exits 1 | `99999999` → exit 1 | ✅ PASS |
| 11 | missing process diagnostic | `Process 99999999 not found` | ✅ PASS |
| 12 | attach without JVM socket exits 1 | 无 socket 时 exit 1 | ✅ PASS |
| 13 | attach failure diagnostic | `Could not start attach mechanism` | ✅ PASS |
| 14 | HotSpot attach trigger file observed | `.attach_pid<PID>` 创建被观测 | ✅ PASS |
| 15 | target received SIGQUIT (handler exit 7) | SIGQUIT 真实投递 | ✅ PASS |
| 16 | trigger file cleaned up (cwd) | 触发文件清理 | ✅ PASS |
| 17 | trigger file cleaned up (JATTACH_PATH) | 回退路径清理 | ✅ PASS |
| 18 | packaged artifact is an AArch64 ELF | 产物格式 | ✅ PASS |

### 3.2 失败的测试

无。

### 3.3 跳过的测试

无。

---

## 四、关键问题分析

### 问题1: AF_UNIX 路径 socket 被拒（EPERM）——attach 正路径不可复现

**现象**：
```
$ python3 -c "...socket.bind('$TMPDIR/x.sock')..."
PermissionError: [Errno 1] Operation not permitted
# /tmp: OSError [Errno 30] Read-only file system (erofs)
# /dev/shm: PermissionError [Errno 13] Permission denied
# abstract socket / socketpair: OK
```

**根因分析**：HarmonyOS HMMAC 对非应用进程（shell/worker 会话）拒绝文件系统
socket 创建；知识库 E461 已记录该能力矩阵。

**解决方案**：与 jattach 无关——attach socket 由目标 JVM 进程自身创建，
jattach 只执行 `connect()`。测试改为对可复现的触发/信号路径做真实断言
（触发文件创建→SIGQUIT 投递→清理），并如实记录该限制。

### 问题2: semget/semop 触发 SIGSYS

**现象**：
```
Signal 31 (core dumped)   # OpenJ9 路径 notify_semaphore() 调用 semget
```

**根因分析**：HarmonyOS seccomp 拦截 SysV 信号量 syscall（知识库 E246 同类
模式；另有 SysV IPC 草稿）。

**解决方案**：OpenJ9 路径仅用于 IBM OpenJ9 JVM，HarmonyOS 无 JVM 运行环境，
该分支不可达；不引入无意义补丁，如实记录为平台限制。

---

## 五、测试环境

```
OS:        HarmonyOS 6.1.0.117 / HongMeng Kernel 1.12.0 aarch64 (HAD-W32)
SDK:       OHOS SDK 26.0.0.18 native (clang 15.0.4, aarch64-unknown-linux-ohos)
Conan:     2.29.1 (OHOS-adapted), profile ohos-aarch64 / ohos-aarch64-device
构建:      make -j1 CC=<ohos clang>  （上游 Makefile，无 configure，零补丁）
产物:      bin/jattach（35200 B, aarch64 musl PIE ELF）
```

---

*报告生成时间: 2026-09-20*
