# DRAFT — HarmonyOS seccomp 拦截 Linux 私有 syscall

> 关联 PR: !3958 | 关联 kv: knowledge/graph/draft/DRAFT-seccomp-blocked-syscall.kv

## 错误特征

进程收到 `SIGSYS` 信号（signal 31）并 core dump（exit 159），`siginfo_t` 中：
- `si_signo = 31`（SIGSYS）
- `si_code = 1`（`SYS_SECCOMP`，seccomp 过滤器触发）
- `si_syscall = N`（被拦截的 syscall 号，如 adjtimex 在 aarch64 上为 171）

典型输出：
```
Signal 31 (core dumped)
# 或探测程序: == SIGSYS caught == si_signo=31 si_code=1 syscall=171 errno=0
```

## 触发条件

- 阶段：runtime
- 平台：HarmonyOS aarch64 with seccomp sandbox
- 典型工具：adjtimex、ntp 客户端、资源控制、命名空间类工具（调用 Linux 私有 syscall 且鸿蒙无等价安全许可）

## 与 E051/E164 的区别

| 条目 | 根因 | 信号可捕获性 | 阶段 |
|------|------|-------------|------|
| E051 | 内核未实现 syscall（setreuid/setregid） | ❌ 不可捕获，进程直接终止 | runtime |
| E164 | 编译期 adjtime 函数缺失，需用 adjtimex 替代 | — | compilation |
| 本条目 | 已实现但被 seccomp 策略拦截（si_code=1=SYS_SECCOMP） | ✅ 可捕获，si_syscall 携带 syscall 号 | runtime |

三者根因、捕获性、适配策略均不同，本条目是独立且可复用的诊断增量。

## 根因分析

HarmonyOS 沙箱 seccomp 策略直接拦截部分 Linux 私有 syscall（如 `adjtimex`，aarch64 编号 171）。
该策略**不可被应用层修改**（无 ptrace/seccomp 解除接口），调用必然触发 SIGSYS 终止进程。

附带发现：`linux/timex.h` 与 musl 头文件存在重定义冲突（timespec/timeval/itimerval/timezone/timex），
上游源码仅 include `sys/timex.h` 时不受影响。

## 解决方案

### 推荐方案（graceful degradation）

检测 SIGSYS 后降级/跳过受限功能，或仅保留不触发受限 syscall 的功能子集：

```c
/* 信号处理中读取 si_syscall 判断 */
struct sigaction sa;
sa.sa_sigaction = on_sigsys;
sa.sa_flags = SA_SIGINFO;
sigaction(SIGSYS, &sa, NULL);

void on_sigsys(int sig, siginfo_t *si, void *uc) {
    printf("si_signo=%d si_code=%d syscall=%d\n",
           si->si_signo, si->si_code, si->si_syscall);
    exit(1);
}
```

### smoke test 策略

使用不触发受限 syscall 的路径（如 `--version`），退出码 0：
```bash
adjtimex --version   # 正常输出 "adjtimex 1.29"，exit 0
```

## 验证命令

```bash
adjtimex --print                     # 预期: Signal 31 (core dumped)
syscall(SYS_adjtimex, &tx)           # 预期: SIGSYS si_code=1=SYS_SECCOMP
adjtimex --version; echo $?          # 预期: 0（不触发受限 syscall）
```

## 复用范围

所有调用 Linux 私有 syscall 且鸿蒙无等价安全许可的工具类库：
时间调整（adjtimex、ntp 客户端）、资源控制、命名空间、系统管理工具等。
识别特征（SIGSYS + si_code=1=SYS_SECCOMP + si_syscall=N）与降级策略可跨库直接复用。

## 恢复条件

- **无应用层恢复手段**：鸿蒙 seccomp 策略不可被应用层修改
- 适配建议：graceful degradation（检测 SIGSYS 后降级/跳过）或仅保留不触发受限 syscall 的功能子集
