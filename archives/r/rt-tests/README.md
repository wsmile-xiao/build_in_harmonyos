# rt-tests

> Linux 实时测试套件：`cyclictest`、`signaltest`、`sigwaittest`、`ptsematest`、
> `hackbench`、`pi_stress`、`pip_stress`、`rt-migrate-test`、`oslat`、
> `cyclicdeadline`、`deadline_test`、`queuelat`、`ssdd` 等。

## 简介

rt-tests 2.10 用 C 写成，构建系统是上游手写的 `Makefile`（无 autotools）。
每个工具是一个独立可执行文件，产物安装到 `bin/`。

## OHOS 适配要点

- **POSIX 特性宏**：bionic 的 `<unistd.h>` 不定义 `_POSIX_THREAD_PRIO_INHERIT`，
  但 `pthread_mutexattr_setprotocol(PTHREAD_PRIO_INHERIT)` 在真机返回 0（可用）。
  用 `-D_POSIX_THREAD_PRIO_INHERIT=200809L` 启用，避免上游直接 `#error` 关掉 pi_stress。
- **getcpu**：上游用 glibc 专有的 `getcpu()`；bionic 提供 `sched_getcpu()`
  （其 `__NR_getcpu` 系统调用被 seccomp 以 SIGSYS 拦截）→ `-DHAVE_SCHED_GETCPU`。
- **无 libnuma**：制品仓无 libnuma、OHOS 无 NUMA 拓扑 → `RT_NO_NUMA=1`，NUMA 辅助函数
  在补丁里降级为单节点实现（cyclictest/signaltest/oslat 因此不含 `--numa`、
  `--deepest-idle-state`）。`no_libcpupower=1`。
- **pthread affinity**：bionic 无 `pthread_setaffinity_np`/`pthread_getaffinity_np`/
  `pthread_attr_setaffinity_np` → 补丁在 `bionic.h` 里补 shim（bionic 有 barrier，
  故不能用上游的 `PTHREAD_BIONIC` 全套，需 `BIONIC_NO_BARRIERS` 分开控制）。
- **SIGEV_THREAD_ID**：bionic 不暴露，cyclictest 回退到 `SIGEV_SIGNAL`。
- **CFLAGS**：上游默认带 gcc 专有拼写（`-Wno-error=format-truncation=`、`-Wno-nonnull`），
  clang 在 `-Werror` 下直接报未知选项 → 补丁替换为 clang 兼容版本。
- **pmqtest 不构建**：POSIX 消息队列 `mq_*` 在 OHOS 只存在于**静态** `libc.a`，
  不在链接器解析的共享 `libc.so` 里，无法链接。

## 平台限制

非 root 用户没有 `CAP_SYS_NICE`，`sched_setscheduler(SCHED_FIFO)` 返回 EPERM，
因此 `cyclictest` 等测量工具的实时主循环无法在普通用户下运行；需要实时测试时
请以 root 运行或加入实时组。`hackbench`/`pi_stress`/`pip_stress` 可不依赖实时权限运行。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| 无 | - | 仅 C 标准库 |

## 构建与验证

```sh
conan create archives/r/rt-tests/2.10 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

## 参考

- [上游仓库](https://git.kernel.org/pub/scm/utils/rt-tests/rt-tests.git/)
- [Debian 源包](https://sources.debian.org/src/rt-tests/2.10-1/)
