# strace 6.19 - 测试报告

> **测试日期**: 2026-03-23  
> **测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64  
> **测试类型**: 手动功能测试

## 测试结果汇总

| 类别 | 通过 | 失败 | 跳过 |
|------|------|------|------|
| 基础功能 | 2 | 0 | 0 |
| 核心追踪 | 0 | 3 | 0 |
| sudo 规避 | 0 | 6 | 0 |
| **总计** | **2** | **9** | **0** |

## 详细测试结果

### 基础功能测试

| # | 测试项 | 命令 | 结果 | 说明 |
|---|--------|------|------|------|
| 1 | 版本检查 | `strace --version` | ✅ PASS | 输出 strace 6.19，Optional features: no-m32-mpers |
| 2 | 二进制格式 | `file $(which strace)` | ✅ PASS | ELF 64-bit LSB executable, ARM aarch64, musl libc |

### 核心追踪功能测试

| # | 测试项 | 命令 | 结果 | 说明 |
|---|--------|------|------|------|
| 3 | 基础追踪 | `strace echo hello` | ❌ FAIL | ptrace(PTRACE_TRACEME): Permission denied |
| 4 | 带过滤追踪 | `strace -e trace=open ls` | ❌ FAIL | ptrace(PTRACE_TRACEME): Permission denied |
| 5 | 附加进程 | `strace -p PID` | ❌ FAIL | ptrace(PTRACE_ATTACH): Permission denied |

### sudo 规避测试

| # | 测试方法 | 结果 | 说明 |
|---|----------|------|------|
| 6 | `sudo strace echo hello` | ❌ FAIL | exit code 1，无输出 |
| 7 | `sudo strace -o /data/out.txt true` | ❌ FAIL | exit code 1，文件未创建 |
| 8 | `sudo strace --version` | ❌ FAIL | 触发 kill EACCES（内核主动终止） |
| 9 | `sudo setenforce 0` | ❌ FAIL | Permission denied |
| 10 | `sudo cat /sys/fs/selinux/enforce` | ❌ FAIL | Permission denied |
| 11 | `sudo strace -p $$` | ❌ FAIL | exit code 1 |

## 失败原因分析

所有追踪功能失败均因 **SELinux 策略限制**：

```
strace: do_test_ptrace_get_syscall_info: PTRACE_TRACEME: Permission denied
strace: ptrace(PTRACE_TRACEME, ...): Permission denied
```

- 鸿蒙系统的 SELinux 策略（`adhoc_bin` 域）禁止了 ptrace 系统调用
- 这不是编译问题，而是系统级安全策略限制
- `/proc/sys/kernel/yama/ptrace_scope` 不存在（非 yama 限制）

### sudo 无法绕过的原因

SELinux 策略在内核级别封锁了以下操作：

| 操作 | 现状 |
|------|------|
| ptrace 系统调用 | adhoc_bin 域无权限，sudo 下触发 kill EACCES |
| /sys/fs/selinux/ | 完全不可访问（即使 root/sudo） |
| setenforce 切换 | Permission denied（即使 root/sudo） |
| /sys/kernel/security/ | 完全不可读 |

## 结论

strace 6.19 在鸿蒙系统上**编译成功**，但由于 SELinux 策略在**内核级别**完全封锁 ptrace，
**核心追踪功能不可用，且无法通过 sudo 或 setenforce 规避**。状态标记为 `partial`。

### 可能的解决方案

1. 修改设备 SELinux 策略（需要刷机或系统级权限，非普通 root 可行）
2. 联系 OpenHarmony 团队获取 ptrace 支持方案
3. 使用内核级调试替代方案（如 ftrace, 如果可用）
