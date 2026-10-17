# DRAFT-ohos-syscall-capability-matrix-fork-probe — OHOS syscall 能力矩阵与「fork 逐项探测」

> 配套：procenv 0.51 适配（contrib-9733）。procenv 本身就是"平台能力探测工具"，
> 移植它的过程中实测出一张可复用的 **OHOS syscall 能力矩阵**，以及一个**非直觉的探测方法学**。

## 错误特征

单进程一次探测多个 syscall 时，进程会**毫无提示地死掉**，且退出码是 159：

```
Signal 31 (core dumped)
# 或 shell 层：
$ ./probe; echo $?
159
```

（signal 31 = **SIGSYS**；OHOS 对未实现的 syscall 直接以 SIGSYS 终止进程，
**不是**返回 `ENOSYS`，也**无法**用用户态 signal handler 捕获。）

## 触发条件

- 平台：OHOS / HongMeng Kernel（aarch64）
- 阶段：runtime / testing（探测或运行期调用时）
- 代码模式：`syscall(SYS_xxx, ...)` 调用 Linux 专有 syscall；或任何"遍历探测"的探针

## 根因分析

OHOS 内核对**未实现**的 syscall 走的是"SIGSYS 终止"，这与 Linux 常见的三种表现都不同：

| 表现 | 含义 | 能否捕获/降级 |
|------|------|--------------|
| **SIGSYS（signal 31, exit 159）** | 内核未实现该 syscall | ❌ 内核直接终止，handler 无效 |
| `ENOSYS`（errno 38） | 内核"知道"但未实现/未启用 | ✅ 可捕获并降级 |
| 其他 errno（EFAULT/EINVAL/EBADF…） | 参数/权限问题 → **syscall 存在** | ✅ 正常 |

因此：

1. **单进程连续探测会失真**：第一个未实现项就杀掉探针，后面的结果全丢。
   （本任务第一版探针就在 `memfd_create` 之后整片死掉，误以为后续也不可用。）
2. **不能靠返回值判断**：对 SIGSYS 项必须在**调用前**做能力探测并降级（禁止平台宏 `#ifdef __OHOS__`
   （与仓库 E051/P008 的原则一致）。
3. **探测必须每项 fork 子进程**，用 `WIFSIGNALED(st) && WTERMSIG(st) == 31` 区分三态。

## 解决方案

### 探测方法（可复用）

```c
/* 每项 fork 一个子进程；父进程按"是否被 signal 31 杀死"分类 */
for (i = 0; i < n_tests; i++) {
    pid_t p = fork();
    if (p == 0) { errno = 0; tests[i](); printf("errno=%d\n", errno); _exit(0); }
    int st = 0; waitpid(p, &st, 0);
    if (WIFSIGNALED(st) && WTERMSIG(st) == 31) puts("SIGSYS 未实现");
    else if (WIFSIGNALED(st))                 printf("异常信号 %d\n", WTERMSIG(st));
}
```

### 实测能力矩阵（OHOS aarch64，2026-09-16）

| 类别 | syscall |
|------|---------|
| **SIGSYS（未实现，调用即杀进程）** | `fanotify_init`、`keyctl`、`add_key`、`clone3`、`openat2`、`rseq`、`unshare`、`setns`、`bpf`、`mount(2)`、`swapon`、`kexec_load`、`reboot` |
| **ENOSYS（可捕获）** | `userfaultfd`、`pidfd_getfd` |
| **可用** | `memfd_create`、`pidfd_open`、`io_uring_setup`、`seccomp`、`statx`、`copy_file_range`、`splice`、`tee`、`sendfile`、`vmsplice`、`getrandom`、`process_vm_readv`、`perf_event_open`、`ioprio_set`、`quotactl`、`mknodat`、`posix_openpt/grantpt/unlockpt/ptsname` + `/dev/pts/N`（**pty 完整可用**） |

同时实测的 `/sys`、`/dev` 存在性（供移植侦察参考）：

- 存在：`/sys/class/{thermal,leds,drm,gpio,power_supply,backlight,tty,input}`、`/sys/bus/{usb,pci,i2c,spi}`、`/dev/{null,urandom,shm,tty,ptmx,pts}`
- 缺失：`/sys/class/{hwmon,pwm,i2c-dev}`、`/sys/kernel/mm/transparent_hugepage`、`/dev/{mem,kmsg,input/event0,dri/card0,fb0,i2c-0,spidev0.0,gpiochip0,video0,console,fuse,net/tun,uinput}`
- 存在但 **EACCES**：`/proc/filesystems`、`/proc/version`、`/proc/<pid>/fdinfo` 目录缺失（读 `/proc/self/fdinfo/*` 报 No such file or directory）

### 守卫方式：优先运行时/配置期探测，避免平台宏

syscall 可用性是**内核/平台**属性（同一内核上 glibc/musl 相同），因此守卫**首选**

- **运行时探测**：先尝试调用，失败即降级（注意 SIGSYS 项无法 try/catch，需靠前面的 fork 探测先分类）；
- **配置期探测**：configure/CMake 里 AC_CHECK_*/check_symbol_exists 得出 HAVE_*，用该宏守卫；

**不要**用 #ifdef __OHOS__ 之类的平台宏（仓库 R8 红线，本 PR 的 AI 检视已因此把补丁判为 P1）。确需编译期守卫时，才用 libc 特性宏（如 !defined(__GLIBC__)）并说明 R8 例外判据。

### 禁止做法

- ❌ **单进程连续探测多个 syscall 后按返回值判断**：第一个 SIGSYS 项就让结论整体失真。
- ❌ **试图用 signal handler 捕获 SIGSYS**：内核直接终止进程，handler 无效（P008 已列为 critical）。
- ❌ 把 `ENOSYS` 与 `SIGSYS` 混为一谈：前者可降级，后者必须调用前守卫。

## 验证

```sh
# fork 探针（本任务实测）
#   SIGSYS 项示例：timeout 5 ./probe  → 会被 signal 31 终止（在单进程版中）
#   分类后：13 项 SIGSYS / 2 项 ENOSYS / 16 项可用
# 与 procenv 的关系：procenv 的 -b/--libs 与 -i/--misc 在 OHOS 上忙等自旋（持 AF_INET socket），
#   无参数全量 dump 因此挂起 —— 这是访问接口信息时的另一类平台行为，已在 procenv 报告中单列。
```

## 查重差异

- **E051** 是"**单个** syscall（`setreuid`）未实现 → SIGSYS → 必须调用前拦截"的**原则性条目**；
  本条补充的是**批量能力发现的方法学**（必须 fork 逐项探测，否则探针自杀）与**实测矩阵**
  （哪些缺、哪些是 ENOSYS、哪些可用），面向"移植前的平台侦察/能力盘点"这一使用场景。
- 与 `E085/E127/E507`（pthread 取消接口）无关：那些是**用户态 libc 接口**缺失，本条是**内核 syscall** 层。

## 元信息

- authors: `frj__`（contributor_id: `frj__`）
- source_event: procenv 0.51 OHOS aarch64 适配期间的能力矩阵实测（2026-09-16）
- draft: true —— 待主编审核后 promote 为正式 E 条目
