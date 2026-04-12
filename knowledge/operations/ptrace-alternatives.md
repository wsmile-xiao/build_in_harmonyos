# 鸿蒙系统 ptrace 限制及替代方案

> **更新日期**: 2026-03-23  
> **测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64  
> **SELinux 上下文**: `u:r:adhoc_bin:s0`

---

## 1. 问题概述

strace 依赖 ptrace 系统调用，但鸿蒙系统的 SELinux 策略在内核级别完全封锁了 ptrace，
导致 strace 编译后无法执行实际追踪。sudo 和 setenforce 均无法绕过。

---

## 2. 封锁层级分析

### 2.1 权限封锁范围

| 操作 | 普通用户 | sudo | 说明 |
|------|:--------:|:----:|------|
| `ptrace(PTRACE_TRACEME)` | ❌ EACCES | ❌ kill EACCES | 内核主动终止进程 |
| `/sys/fs/selinux/*` | ❌ | ❌ | 完全不可读 |
| `setenforce 0` | ❌ | ❌ | Permission denied |
| `/sys/kernel/security/*` | ❌ | ❌ | 完全不可读 |
| `/sys/kernel/debug/tracing/` | ❌ | ❌ | debugfs 已挂载但不可访问 |
| `/proc/self/syscall` | ❌ 不存在 | ❌ 不存在 | 内核未导出此文件 |
| `LD_PRELOAD` | ✅ | ✅ | 可用 |

### 2.2 封锁原理

```
用户进程 (adhoc_bin:s0)
    │
    ├─► strace 调用 ptrace(PTRACE_TRACEME)
    │       └─► 内核 LSM 检查 → 无 allow 规则 → EACCES
    │
    ├─► sudo strace
    │       └─► 仍在受限域 → kill EACCES（进程被杀）
    │
    └─► sudo setenforce 0
            └─► SELinux 接口不可写（系统级锁定）
```

**结论**：这不是简单的 SELinux boolean 或 DAC 权限问题，而是系统级的硬性安全策略。

---

## 3. 替代方案调查

### 3.1 方案总览

| 方案 | 原理 | 需要 ptrace? | 鸿蒙可用 | 适用场景 |
|------|------|:------------:|:--------:|----------|
| ftrace | 内核 tracepoint | 否 | ❌ | 内核调试 |
| perf | perf_event 子系统 | 否 | ❌ | 性能分析 |
| eBPF/bpftrace | 内核虚拟机 | 否 | ❌ | 高级追踪 |
| auditd | 内核审计框架 | 否 | ❌ | 安全审计 |
| **ltrace** | **动态库 hook (ptrace)** | **是** | **❌** | **库函数追踪** |
| **latrace** | **LD_AUDIT 接口** | **否** | **待验证** | **库函数追踪** |
| **LD_PRELOAD** | **libc 函数拦截** | **否** | **✅** | **用户态函数追踪** |

### 3.2 各方案详情

#### ❌ ftrace（不可用）
- debugfs 已挂载，但 `/sys/kernel/debug/tracing/` 目录权限被 SELinux 封锁
- 即使 sudo 也无法读取 tracing 目录
- 需要系统级权限才能解锁

#### ❌ perf（不可用）
- 系统未安装 perf
- `perf_event_paranoid` 不可读，可能也被锁定

#### ❌ eBPF / bpftrace（不可用）
- 未安装相关工具（bpftool、bpftrace、bcc）
- `/sys/fs/bpf` 不可访问

#### ❌ ltrace（理论上也不可用）
- ltrace 虽然追踪的是库函数调用，但底层仍依赖 ptrace
- 在标准 Linux 上 ltrace 使用 ptrace 来插入断点和读取参数
- **鸿蒙上 ltrace 同样会被 SELinux 阻止**（但尚未实际测试编译/运行）

#### ❓ latrace（待验证）
- 原理：利用 glibc 的 `LD_AUDIT` 接口（`la_symbind*` 系列回调）
- **不依赖 ptrace**，理论上可以在鸿蒙上工作
- 但 musl libc 可能不支持 LD_AUDIT 接口
- 来源：https://latrace.sourceforge.net/

#### ✅ LD_PRELOAD（已验证可用）

**原理**：通过环境变量 `LD_PRELOAD` 加载自定义共享库，用 `dlsym(RTLD_NEXT, ...)` 
获取原始函数指针，在调用前后插入日志代码。

**鸿蒙实测**：
```
# 追踪 wc -l /dev/null
LD_PRELOAD=$TMPDIR/libhook.so wc -l /dev/null

# 输出日志：
open("/dev/null", 0x0)
read(4, 262144) = 0
```

---

## 4. LD_PRELOAD 使用指南

### 4.1 基础 hook 库

以下是一个可用的基础 hook 库实现：

```c
// hook.c - 基础 libc 函数拦截库
#define _GNU_SOURCE
#include <stdio.h>
#include <dlfcn.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

static FILE *logfile = NULL;

static void init_log(void) {
    if (!logfile) {
        const char *tmpdir = getenv("TMPDIR");
        if (!tmpdir) tmpdir = "/tmp";
        char path[512];
        snprintf(path, sizeof(path), "%s/hook_trace.log", tmpdir);
        logfile = fopen(path, "a");
        setvbuf(logfile, NULL, _IONBF, 0);  // 无缓冲，实时输出
    }
}

// 拦截 open()
typedef int (*orig_open_t)(const char *pathname, int flags, ...);
int open(const char *pathname, int flags, ...) {
    orig_open_t orig = dlsym(RTLD_NEXT, "open");
    init_log();
    if (logfile) fprintf(logfile, "open(\"%s\", 0x%x)\n", pathname, flags);
    return orig(pathname, flags, 0);
}

// 拦截 openat()
typedef int (*orig_openat_t)(int dirfd, const char *pathname, int flags, ...);
int openat(int dirfd, const char *pathname, int flags, ...) {
    orig_openat_t orig = dlsym(RTLD_NEXT, "openat");
    init_log();
    if (logfile) fprintf(logfile, "openat(%d, \"%s\", 0x%x)\n", dirfd, pathname, flags);
    return orig(dirfd, pathname, flags, 0);
}

// 拦截 read()（过滤 stdin/stdout/stderr）
typedef ssize_t (*orig_read_t)(int fd, void *buf, size_t count);
ssize_t read(int fd, void *buf, size_t count) {
    orig_read_t orig = dlsym(RTLD_NEXT, "read");
    ssize_t ret = orig(fd, buf, count);
    init_log();
    if (logfile && fd > 2) fprintf(logfile, "read(%d, %zu) = %zd\n", fd, count, ret);
    return ret;
}

// 拦截 write()（过滤 stdin/stdout/stderr）
typedef ssize_t (*orig_write_t)(int fd, const void *buf, size_t count);
ssize_t write(int fd, const void *buf, size_t count) {
    orig_write_t orig = dlsym(RTLD_NEXT, "write");
    init_log();
    if (logfile && fd > 2) fprintf(logfile, "write(%d, %zu)\n", fd, count);
    return orig(fd, buf, count);
}

// 拦截 execve()
typedef int (*orig_execve_t)(const char *pathname, char *const argv[], char *const envp[]);
int execve(const char *pathname, char *const argv[], char *const envp[]) {
    orig_execve_t orig = dlsym(RTLD_NEXT, "execve");
    init_log();
    if (logfile) {
        fprintf(logfile, "execve(\"%s\"", pathname);
        for (int i = 0; argv && argv[i]; i++) fprintf(logfile, ", \"%s\"", argv[i]);
        fprintf(logfile, ")\n");
    }
    return orig(pathname, argv, envp);
}
```

### 4.2 编译和使用

```bash
# 编译 hook 库
clang -shared -fPIC -o $TMPDIR/libhook.so hook.c -ldl

# 使用：追踪任意命令
rm -f $TMPDIR/hook_trace.log
LD_PRELOAD=$TMPDIR/libhook.so <command> [args...]

# 查看追踪日志
cat $TMPDIR/hook_trace.log
```

### 4.3 LD_PRELOAD 的局限性

| 能力 | strace (ptrace) | LD_PRELOAD |
|------|:---------------:|:----------:|
| 拦截 libc 函数（open/read/write...） | ✅ | ✅ |
| 拦截直接系统调用（`syscall()` / 内联汇编） | ✅ | ❌ |
| 追踪已运行的进程（`strace -p PID`） | ✅ | ❌ |
| 追踪静态链接程序 | ✅ | ❌ |
| 查看完整内核返回值和寄存器 | ✅ | ❌ |
| 追踪信号 | ✅ | ❌ |
| 无需修改目标程序 | ✅ | ✅ |
| 需要特殊权限 | ❌ | ❌ |

### 4.4 扩展建议

可以继续 hook 的常用函数：

```c
// 文件操作
close(), unlink(), rename(), stat(), fstat(), lstat()
readlink(), symlink(), chmod(), chown(), mkdir(), rmdir()

// 内存操作
mmap(), munmap(), mprotect(), brk()

// 网络操作（需 #include <sys/socket.h>）
socket(), bind(), connect(), listen(), accept(), send(), recv()

// 进程操作
fork(), clone(), waitpid(), getpid(), getppid()

// 信号
signal(), sigaction()
```

---

## 5. 已知工具对比

### 5.1 ltrace（需要 ptrace，鸿蒙不可用）

| 项目 | 说明 |
|------|------|
| 官网 | http://www.ltrace.org/ |
| 仓库 | https://sourceware.org/git/?p=ltrace.git |
| 许可 | GPL-2.0 |
| 原理 | 通过 ptrace 插入断点，追踪动态库函数调用 |
| ptrace 依赖 | **是**（在 PLT/GOT 层面插入断点需要 ptrace） |
| 鸿蒙可用 | ❌（ptrace 被封锁） |
| 备注 | 虽然追踪的是库函数，但底层机制仍依赖 ptrace |

### 5.2 latrace（可能可用，待验证）

| 项目 | 说明 |
|------|------|
| 官网 | https://latrace.sourceforge.net/ |
| 许可 | GPL-2.0 |
| 原理 | 利用 glibc 的 LD_AUDIT 接口（la_symbind* 回调） |
| ptrace 依赖 | **否** |
| 鸿蒙可用 | ❓（需测试 musl 是否支持 LD_AUDIT） |
| 备注 | musl libc 可能不支持 LD_AUDIT，如不支持则无法使用 |

### 5.3 手动 LD_PRELOAD hook（已验证可用）

| 项目 | 说明 |
|------|------|
| 实现 | 自定义共享库 + dlsym(RTLD_NEXT) |
| ptrace 依赖 | **否** |
| 鸿蒙可用 | ✅ 已验证 |
| 优势 | 简单、可控、可定制 |
| 劣势 | 需要为每个函数手动编写 hook；无法追踪直接系统调用 |

---

## 6. 总结与建议

### 当前鸿蒙环境下的最佳实践

```
需要调试时：
    │
    ├─► 追踪库函数调用 → LD_PRELOAD hook 库 ✅
    │       - 适用于：排查文件操作、IO、进程创建等
    │       - 限制：无法追踪静态链接程序和直接系统调用
    │
    ├─► 追踪库函数调用 → 尝试编译 ltrace/latrace ❓
    │       - ltrace：需 ptrace，预计不可用
    │       - latrace：需 LD_AUDIT，musl 支持待确认
    │
    └─► 内核级追踪 → 无可用方案 ❌
            - ftrace/perf/eBPF 全被 SELinux 封锁
            - 需要系统级权限或 OpenHarmony 官方支持
```

### 对 MISSING_TOOLS.md 的影响

strace 状态已标记为 `partial`（编译成功但 ptrace 受限），建议：
1. 保留 strace 编译档案，记录 ptrace 限制
2. LD_PRELOAD hook 库作为实际可用的调试工具
3. 如需更完善的工具，可考虑编写一个 strace 风格的 LD_PRELOAD 包装器

---

*文档版本: 1.0*  
*最后更新: 2026-03-23*  
*关联档案: archives/s/strace/6.19/*
