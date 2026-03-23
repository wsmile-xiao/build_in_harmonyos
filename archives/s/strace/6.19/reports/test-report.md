# strace 6.19 测试报告

**测试日期**: 2026-03-23  
**测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64  
**安装路径**: /storage/Users/currentUser/usr/local/bin/strace

---

## 测试结果摘要

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 版本信息显示 | ✅ 通过 | `strace --version` 正确输出 |
| 进程追踪功能 | ❌ 失败 | PTRACE_TRACEME 被 SELinux 拒绝 |

**总计**: 1 通过 / 1 失败

---

## 测试详情

### 测试 1: 版本信息显示 ✅

```bash
$ /storage/Users/currentUser/usr/local/bin/strace --version
strace -- version 6.19
Copyright (c) 1991-2025 The strace developers <https://strace.io>.
...
```

**结果**: 成功。二进制文件可正常执行，输出了正确的版本号 6.19。

### 测试 2: 进程追踪功能 ❌

```bash
$ /storage/Users/currentUser/usr/local/bin/strace ls
strace: test_ptrace_setoptions_follow: PTRACE_TRACEME: Permission denied
strace: ptrace(PTRACE_TRACEME, ...): Permission denied
```

**结果**: 失败。`PTRACE_TRACEME` 系统调用返回 `Permission denied`。

**原因分析**:
- HarmonyOS 内核的 SELinux 策略禁止用户空间进程使用 `ptrace` 系统调用
- 这是内核级别的安全限制，无法通过编译选项或用户空间配置解决
- 即使使用 root 权限也可能受到限制

**影响**:
- strace 的核心功能（系统调用追踪）完全不可用
- 二进制文件本身编译正确，但作为工具无法发挥其作用

---

## 结论

strace 6.19 在 HarmonyOS 上**编译成功**但**功能不可用**。运行时被 SELinux 策略阻止使用 `ptrace`，这是系统级安全限制。除非 HarmonyOS 放开 ptrace 策略，否则 strace 无法在此平台上实际使用。

**建议**: 如果需要调试系统调用，可考虑使用 `gdb`（系统已预装 gdb 16.3），虽然功能不如 strace 方便，但可能受 SELinux 策略限制较少。
