# `__OHOS__` 通用适配模式指南

> 从 Python 3.9.0 移植的 23 个补丁中提炼出的通用适配模式，适用于所有需要从 Linux 移植到 HarmonyOS 的 C/C++ 项目。

---

## 目录

1. [核心原则](#1-核心原则)
2. [需要加 `__OHOS__` 的模式（内核 API 复用）](#2-需要加-__ohos__-的模式内核-api-复用)
3. [不应加 `__OHOS__` 的模式（glibc 特有）](#3-不应加-__ohos__-的模式glibc-特有)
4. [Python 层面适配模式](#4-python-层面适配模式)
5. [configure.ac 适配清单](#5-configureac-适配清单)
6. [决策流程图](#6-决策流程图)

---

## 1. 核心原则

HarmonyOS 的内核基于 Linux，但用户态使用 **musl libc** 而非 glibc，且有 **SELinux** 限制。因此适配时需要区分三个层次：

| 层次 | 说明 | `__OHOS__` 策略 |
|------|------|----------------|
| **内核 API（syscall）** | fork、gettid、sendfile 等 | ✅ 可复用 `__linux__` 条件（加 `\|\| defined(__OHOS__)`） |
| **glibc 特有 API** | confstr、mallinfo2、error_message_stack 等 | ❌ 不能复用（musl 有不同实现或缺失） |
| **系统路径和布局** | /sbin/ldconfig、/proc/self/fd 等 | ❌ 不能复用（鸿蒙使用 Android-like 布局） |

### 三层判断口诀

```
内核 syscall → 复用（加 __OHOS__）
glibc 特有   → 不加（musl 不同）
系统路径     → 不加（单独处理）
```

---

## 2. 需要加 `__OHOS__` 的模式（内核 API 复用）

以下场景中，鸿蒙内核与 Linux 内核行为一致，可以复用 `__linux__` 条件。

### 2.1 线程相关：gettid()

**背景**：`gettid()` 是一个系统调用，鸿蒙内核支持。

```c
// gettid() — 鸿蒙内核支持
#if defined(__linux__) || defined(__OHOS__)
#   include <sys/syscall.h>
    // 使用 SYS_gettid 获取线程 ID
    pid_t tid = (pid_t)syscall(SYS_gettid);
#endif
```

**要点**：这是内核 syscall，不依赖 glibc，鸿蒙内核直接支持。

---

### 2.2 文件描述符路径：/dev/fd

**背景**：鸿蒙可能不挂载 `/proc`，因此不能依赖 `/proc/self/fd`。

```c
// /dev/fd 路径（鸿蒙可能不挂载 /proc）
#if defined(__FreeBSD__) || (defined(__APPLE__) && defined(__MACH__)) || defined(__OHOS__)
#   define FD_DIR "/dev/fd"
#else
#   define FD_DIR "/proc/self/fd"
#endif
```

**要点**：鸿蒙与 BSD/macOS 一样，应使用 `/dev/fd` 而非 `/proc/self/fd`。

---

### 2.3 sendfile 系统调用

**背景**：`sendfile()` 的 NULL offset 行为在鸿蒙内核中与 Linux 一致。

```c
// sendfile NULL offset — 鸿蒙内核支持
#if defined(__linux__) || defined(__OHOS__)
    if (offobj == Py_None) {
        // 当 offset 为 NULL 时，sendfile 从文件当前位置传输
        ret = sendfile(in_fd, out_fd, NULL, count);
    }
#endif
```

**要点**：`sendfile` 是内核 syscall，NULL offset 的语义由内核定义，与 libc 无关。

---

### 2.4 musl 时区处理

**背景**：musl libc（包括鸿蒙 musl）的 `mktime()` 不接受外部 `tzname` 设置，这与 glibc 行为不同。

```c
// musl libc 的 mktime() 不接受外部 tzname（包括鸿蒙 musl）
#if (defined(__linux__) || defined(__OHOS__)) && !defined(__GLIBC__)
    // musl 环境下需要特殊处理时区
    // tzname 被 musl 忽略，需要直接操作环境变量
    setenv("TZ", tz, 1);
    tzset();
#else
    // glibc 环境下可以直接设置 tzname
    tzname[0] = ...;
    tzname[1] = ...;
#endif
```

**要点**：这个模式用 `!defined(__GLIBC__)` 排除了 glibc，同时用 `defined(__OHOS__)` 将鸿蒙纳入 musl 分支。**不要只用 `defined(__linux__) && !defined(__GLIBC__)`**，否则会遗漏鸿蒙。

---

### 2.5 启动时 fd 验证

**背景**：[bpo-32849](https://bugs.python.org/issue32849) 修复了 fd 重定向问题，Linux 和鸿蒙共用 `dup()` 验证方式。

```c
// bpo-32849：fd 重定向问题（Linux 和鸿蒙共用）
#if defined(__linux__) || defined(__OHOS__) || defined(MS_WINDOWS)
    // 使用 dup() 验证 fd 是否有效
    int fd2 = dup(fd);
    if (fd2 >= 0) {
        close(fd2);
        // fd 有效
    }
#else
    // 使用 fstat() 验证 fd 是否有效
    struct stat st;
    if (fstat(fd, &st) == 0) {
        // fd 有效
    }
#endif
```

**要点**：fd 验证方式取决于内核对 dup 的行为，鸿蒙内核与 Linux 一致。

---

### 2.x 未实现 syscall 提前拦截（__OHOS__ 守卫返回 ENOSYS）

**背景**：鸿蒙内核对部分未实现的 syscall 发送 SIGSYS 信号（signal 31），且**不可被信号处理器捕获**，进程直接终止。因此不能依赖信号处理，必须在 C 源码调用前拦截。

**典型代码**：

```c
int some_function(...) {
#ifdef __OHOS__
    /* HarmonyOS: unimplemented syscall sends uncatchable SIGSYS.
       Return ENOSYS to avoid process death. */
    errno = ENOSYS;
    return -1;
#endif
    return actual_syscall(...);
}
```

**已知受影响的 syscall**：

| syscall | SIGSYS 可捕获？ | 正确处理 |
|---------|----------------|---------|
| `setreuid` | ❌ 不可捕获 | **必须**提前拦截 |
| `setregid` | ❌ 不可捕获 | **必须**提前拦截 |
| `clock_settime` | ✅ 可捕获但 errno 不确定 | 建议提前拦截 |
| `chroot` | ✅ 可捕获但返回垃圾值 | 建议提前拦截 |

**为什么信号处理不可行**：
- Python `signal.signal(signal.SIGSYS, handler)` → ❌ 进程仍崩溃
- C `sigaction(SIGSYS, &sa, NULL)` → ❌ setreuid/setregid 不触发 handler

**编译注意**：`__OHOS__` 由鸿蒙 SDK 的 clang 自动定义，无需额外 `-D` 参数。编译器会警告原始 syscall 调用变为不可达代码（`code will never be executed`），这是预期的。

**案例**：Python 3.9.0 补丁 0039（timemodule.c）、0040（posixmodule.c）。详见 `error-patterns.md` E051。

---

## 3. 不应加 `__OHOS__` 的模式（glibc 特有）

以下场景中，API 依赖 glibc 特有实现，鸿蒙的 musl libc 没有这些功能，**不应**加 `__OHOS__`。

### 3.1 glibc 版本检测

**背景**：`__GLIBC__` 和 `__GLIBC_MINOR__` 仅在 glibc 环境下定义，musl 环境下不存在。

```c
// ❌ 不加 __OHOS__：glibc 特有版本检测
#if defined(__linux__) && defined(__GLIBC__) && __GLIBC__ >= 2 && __GLIBC_MINOR__ >= 34
    // glibc 2.34+ 将 pthread 并入 libc，不再需要 -lpthread
    // 鸿蒙使用 musl，不需要此分支
#endif
```

**要点**：`defined(__GLIBC__)` 已经隐式排除了 musl 环境，加 `__OHOS__` 反而会引入错误。

---

### 3.2 glibc 扩展 API

**背景**：musl 没有 `error_message_stack` 等 glibc 扩展。

```c
// ❌ 不加 __OHOS__：musl 没有 error_message_stack
#if defined(__linux__) && defined(__GLIBC__)
    // 使用 glibc 特有的 h_errno error_message_stack
    const char *msg = __h_errno_location();
#endif
```

**要点**：即使看起来功能相似，也不要假设 musl 有 glibc 的扩展 API。应查阅 musl 文档确认。

---

### 3.3 内核头文件特有的特性

**背景**：pidfd 等**新内核 API** 鸿蒙内核不支持，即使 Linux 内核头文件中有定义。

```c
// ❌ 不加 __OHOS__：pidfd 等新内核 API 鸿蒙不支持
#if defined(__linux__) && defined(__NR_pidfd_open)
    // pidfd_open() 系统调用
    // 鸿蒙内核没有实现此 syscall
#endif
```

**要点**：鸿蒙内核基于 Linux 但**并非完整复刻**，新版本的 syscall（如 pidfd、io_uring）可能未移植。

---

### 3.4 系统路径和工具

**背景**：鸿蒙使用 Android-like 文件系统布局，许多 Linux 标准路径不存在。

```c
// ❌ 不加 __OHOS__：鸿蒙没有 /sbin/ldconfig
#if defined(__linux__)
    // 查找共享库缓存
    // 鸿蒙没有 ldconfig，不应加入此分支
#endif
```

**要点**：系统路径问题需要在 Python 层或 configure 层单独处理，参见第 4、5 节。

---

## 4. Python 层面适配模式

### 4.1 sys.platform 判断

**标准模式**：使用 `startswith` 同时兼容 `ohos` 和 `harmonyos` 两种 platform 字符串。

```python
# 标准模式 — 推荐写法
if sys.platform.startswith(('ohos', 'harmonyos')):
    # 鸿蒙特有处理
    pass
```

**为什么不直接 `==` 比较**：不同版本的鸿蒙 Python 构建可能使用不同的 platform 字符串（`ohos`、`ohos-aarch64`、`harmonyos` 等），`startswith` 更健壮。

---

### 4.2 Shell 路径

**背景**：鸿蒙的标准 shell 位于 `/system/bin/sh`，但部分环境可能也有 `/bin/sh`。

```python
# /system/bin/sh 优先，/bin/sh 兜底
if sys.platform.startswith(('ohos', 'harmonyos')):
    shell = '/system/bin/sh' if os.path.exists('/system/bin/sh') else '/bin/sh'
else:
    shell = '/bin/sh'
```

**要点**：使用 `os.path.exists()` 做运行时检测，确保兼容不同鸿蒙版本。

---

### 4.3 PATH 扩展

**背景**：鸿蒙的 `/system/bin` 不在标准 `defpath` 中，需要显式添加。

```python
# 鸿蒙的 /system/bin 不在标准 defpath 中
if sys.platform.startswith(('ohos', 'harmonyos')):
    defpath = '/system/bin:/bin:/usr/bin'
else:
    defpath = '/bin:/usr/bin'
```

**要点**：鸿蒙的大部分系统命令（ls、cp、sh 等）都在 `/system/bin` 下，不添加会导致子进程找不到命令。

---

### 4.4 临时目录

**背景**：鸿蒙的 `/tmp` 可能不可写，`/data/local/tmp` 是可靠的可写临时目录。

```python
# /data/local/tmp 是鸿蒙的可写临时目录
if sys.platform.startswith(('ohos', 'harmonyos')):
    dirlist.extend(['/data/local/tmp', '/tmp', '/var/tmp'])
else:
    dirlist.extend(['/tmp', '/var/tmp'])
```

**要点**：将 `/data/local/tmp` 放在最前面，因为它最可靠；保留 `/tmp` 作为备选。

---

### 4.5 find_library 安全处理

**背景**：鸿蒙没有 `/sbin/ldconfig`，不能尝试调用它来查找共享库。

```python
# 鸿蒙没有 /sbin/ldconfig
if sys.platform.startswith(('ohos', 'harmonyos')):
    return None  # 跳过 ldconfig 路径
```

**要点**：直接返回 `None` 跳过，不要尝试执行 `ldconfig -p`，否则会报错或卡死。

---

## 5. configure.ac 适配清单

从 Python 3.9.0 适配中提炼的 `configure.ac` 常见修改点：

| 修改点 | 说明 | 修改方式 |
|--------|------|----------|
| **MACHDEP** | 目标平台标识 | 设置为 `ohos` |
| **BIND_NOW** | musl 需要立即绑定 | 添加 `-Wl,-z,now` |
| **CAN_RAW_FD_FRAMES** | CAN Socket 扩展 | 跳过检测（鸿蒙不支持） |
| **CAN_RAW_JOIN_FILTERS** | CAN Socket 扩展 | 跳过检测（鸿蒙不支持） |
| **multiarch triplet** | 交叉编译目标三元组 | 使用 `aarch64-linux-ohos` |
| **_XOPEN_SOURCE** | POSIX 功能宏 | 不设置（musl 已默认启用足够的功能） |
| **符号链接** | `ln -s` 在 HMDFS 不可靠 | ⚠️ 所有 `.so/.a` 的 `ln -s` 必须改为 `cp -p`（见[铁律 #1](harmonyos-specifics.md#铁律-1符号链接在-hmdfs-上不可靠必须用-cp-替代-ln-s)） |

### 详细说明

#### MACHDEP
```m4
# configure.ac 中设置平台标识
case $host in
    *-*-ohos*)
        MACHDEP=ohos
        ;;
esac
```

#### BIND_NOW
```m4
# musl libc 需要 BIND_NOW 确保符号立即解析
case $host_os in
    ohos*)
        LDFLAGS="$LDFLAGS -Wl,-z,now"
        ;;
esac
```

#### multiarch triplet
```m4
# 鸿蒙的 multiarch 格式
MULTIARCH="$host_cpu-linux-ohos"
# 例如：aarch64-linux-ohos
```

---

## 6. 决策流程图

这是本指南的**核心内容**，在遇到 `#ifdef __linux__` 条件时，按照以下流程决策：

```
遇到 #ifdef __linux__ 条件
    │
    ├─ Q1: 依赖的是内核 syscall？
    │       │
    │       YES ──→ 加 || defined(__OHOS__)
    │       │        复用 Linux 内核行为
    │       │
    │       │        常见 syscall:
    │       │        ├─ fork(), clone(), gettid()
    │       │        ├─ sendfile(), splice(), tee()
    │       │        ├─ epoll_create(), epoll_ctl()
    │       │        ├─ signalfd(), timerfd_create()
    │       │        ├─ dup(), dup2(), fcntl()
    │       │        └─ /dev/fd, /dev/null, /dev/zero
    │       │
    │       NO ───→ 继续 Q2
    │
    ├─ Q2: 依赖的是 glibc API？
    │       │
    │       YES ──→ 不加 __OHOS__
    │       │        musl 实现不同或缺失
    │       │
    │       │        常见 glibc 特有:
    │       │        ├─ confstr(_CS_GNU_LIBC_VERSION, ...)
    │       │        ├─ error_message_stack (resolv)
    │       │        ├─ mallinfo2(), malloc_info()
    │       │        ├─ __libc_enable_secure
    │       │        ├─ program_invocation_short_name
    │       │        ├─ backtrace_symbols() (需要 libgcc)
    │       │        └─ glibc 版本检测 (__GLIBC__)
    │       │
    │       NO ───→ 继续 Q3
    │
    ├─ Q3: 依赖的是内核头文件定义？
    │       │
    │       YES ──→ 检查鸿蒙内核是否支持
    │       │
    │       │        不支持（不加 __OHOS__）:
    │       │        ├─ pidfd_open(), pidfd_send_signal()
    │       │        ├─ io_uring_setup(), io_uring_enter()
    │       │        ├─ process_mrelease(), process_madvise()
    │       │        └─ landlock_create_ruleset()
    │       │
    │       │        可能支持（需实测验证）:
    │       │        ├─ timerfd_create(), timerfd_settime()
    │       │        ├─ memfd_create()
    │       │        └─ bpf(), seccomp()
    │       │
    │       NO ───→ 继续 Q4
    │
    └─ Q4: 依赖的是系统路径/工具？
            │
            YES ──→ 不加 __OHOS__，单独处理
            │        鸿蒙使用 Android-like 布局
            │
            │        需要单独处理的路径:
            │        ├─ /sbin/ldconfig → 不存在
            │        ├─ /proc/self/fd → 用 /dev/fd 替代
            │        ├─ /bin/sh → 用 /system/bin/sh 替代
            │        ├─ /tmp → 用 /data/local/tmp 替代
            │        ├─ /etc/passwd → 可能不存在或受限
            │        ├─ /etc/nsswitch.conf → 不存在
            │        └─ /usr/lib/ → 用 /system/lib/ 或 /usr/lib/ 替代
```

### 快速参考表

| 条件类型 | 是否加 `__OHOS__` | 示例 |
|----------|-------------------|------|
| 内核 syscall | ✅ 加 | `gettid()`, `sendfile()`, `fork()` |
| `/dev/fd` 路径 | ✅ 加（与 BSD 同组） | `FD_DIR "/dev/fd"` |
| musl 特有行为 | ✅ 加（排除 glibc） | `mktime()` 时区处理 |
| glibc API/扩展 | ❌ 不加 | `confstr`, `error_message_stack` |
| glibc 版本检测 | ❌ 不加 | `__GLIBC__ >= 2.34` |
| 新内核 syscall | ❌ 不加（待验证） | `pidfd_open`, `io_uring` |
| 系统路径 | ❌ 不加（单独处理） | `/sbin/ldconfig`, `/bin/sh` |
| 系统工具 | ❌ 不加（单独处理） | `ldconfig -p` |

---

## 附录：常见问题

### Q: 为什么不用 `defined(__linux__)` 覆盖鸿蒙？

**A**: 鸿蒙内核虽然基于 Linux，但用户态差异很大。`__linux__` 在鸿蒙编译环境中**可能被定义也可能不被定义**，取决于工具链配置。使用显式的 `__OHOS__` 宏更安全、更明确。

### Q: 如何判断一个 API 是内核 syscall 还是 glibc API？

**A**: 简单方法：
1. 查看函数是否在 `man 2`（syscall）还是 `man 3`（libc）
2. 查看 `#include` 是 `<sys/...>` 还是标准头文件
3. 查看 glibc vs musl 文档对比

### Q: musl 和 glibc 有哪些主要差异？

**A**: 详见本目录下的 `musl-glibc-full-comparison-gnu-linux.md` 和 `musl-glibc-full-comparison-iso-posix.md`。

### Q: 鸿蒙的 SELinux 限制会影响到哪些适配？

**A**: 主要影响：
- 文件系统访问（部分路径只读）
- 网络权限（需要签名授权）
- 进程间通信（socket 权限）
- 设备节点访问（/dev 下的节点权限）
