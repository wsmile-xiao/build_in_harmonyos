# rt-tests 2.10 适配笔记

## 版本来源

上游在 kernel.org 发布签名 tarball，Debian 的 `rt-tests_2.10-1` orig tarball 与之
同源树。`conandata.yml` 用 HTTPS 的 kernel.org URL，sha256 `2c796284…` 与
`rt-tests_2.10-1.dsc` 逐字符一致。

## 构建

上游是**手写 Makefile** 项目（无 autotools）。配方用显式目标列表 +
`RT_NO_NUMA=1 no_libcpupower=1` 编译 13 个工具（`pmqtest` 除外，见下），
`package()` 安装到 `bin/`。

真机 `conan create` 过程中定位并修复的 bionic 差异：

| # | 现象 | 根因 | 修法 |
|---|---|---|---|
| 1 | `#error "Can't run this test without PI Mutex support"` | bionic `<unistd.h>` 不定义 `_POSIX_THREAD_PRIO_INHERIT`（实测运行时 `pthread_mutexattr_setprotocol(PRIO_INHERIT)`=0 可用） | `-D_POSIX_THREAD_PRIO_INHERIT=200809L`（保住 pi_stress） |
| 2 | `getcpu()` 未定义 | glibc 专有；`__NR_getcpu` 被 seccomp 以 SIGSYS 拦截 | `-DHAVE_SCHED_GETCPU`，改用 `sched_getcpu()` |
| 3 | `numa.h` 找不到 | 无 libnuma、无 NUMA 拓扑 | `-DRT_NO_NUMA` + 补丁 0001/0005 单节点降级 |
| 4 | 链接 `-lnuma` 失败 | NUMA 库缺失 | Makefile 在 `RT_NO_NUMA=1` 时去掉 `-lnuma`（保留 `-lrttestnuma`） |
| 5 | `pthread_setaffinity_np`/`pthread_attr_setaffinity_np` 未定义 | bionic 无 GNU pthread affinity 扩展 | 补丁 0006 在 `bionic.h` 补 shim |
| 6 | barrier typedef 冲突 | bionic **有** `pthread_barrier_*`，上游 `PTHREAD_BIONIC` 全套会重复定义 | 补丁 0006 用 `BIONIC_NO_BARRIERS` 分开控制，只取 affinity shim |
| 7 | `SIGEV_THREAD_ID` 未定义 | bionic 不暴露 | 补丁 0003 回退 `SIGEV_SIGNAL` |
| 8 | clang 报未知选项 `-Werror=format-truncation=` | 上游默认 CFLAGS 是 gcc 专有拼写 | 补丁 0002 换成 clang 兼容 CFLAGS |
| 9 | `mq_open`/`mq_send`/… 未定义 | OHOS 只在**静态** `libc.a` 有 POSIX mq，共享 `libc.so` 没有 | **不构建 pmqtest**（逐条技术原因） |

另：上游 Makefile 的 `MANPAGES` 在 `PYLIB` 已 `undefine` 时仍会引用 python 手册页
（第 78-80 行），补丁 0002 顺手用 `ifdef PYLIB` 括起来，保证无 python 也能 `make`。

## 测试

上游**无独立测试套件**——工具本身就是交付物。适配后消费者
`test_package/test_rt_tests.sh` **15/15**：12 个工具的 `--help` 版本横幅检查
（编译/链接/可执行证据）+ `hackbench`（不依赖实时权限，实跑出 `Time:`）+
`pi_stress`/`pip_stress`（短时实跑）。

## 平台能力实测（决定路径 A）

真机 aarch64、非 root（euid=20020085）：

| 能力 | 结果 |
| --- | --- |
| `sched_setscheduler(SCHED_FIFO, 80)` | rc=-1 errno=1（EPERM，无 CAP_SYS_NICE） |
| `pthread_setschedparam(SCHED_FIFO)` | rc=22（EINVAL） |
| `mlockall(MCL_CURRENT\|MCL_FUTURE)` | rc=0 |
| `mlock(anon)` | rc=0 |
| `pthread_mutexattr_setprotocol(PRIO_INHERIT)` | rc=0（可用） |
| `sched_getcpu()` | rc=0（可用） |
| `syscall(SYS_getcpu)` | rc=-1 errno=14（EFAULT，被拦截） |

即 rt-tests 可完整构建、可执行多数工具；但**非 root 无法获得 SCHED_FIFO**，实时测量主
循环跑不起来。`pthread_barrier` 缺失、`SIGEV_THREAD_ID`、无 libnuma 等均属已被知识库
（E121/E246 及 `DRAFT-E584` 等 SIGSYS 族、musl/libc 差异族）覆盖或代码内一次性适配，
未构成新的「一类、0 命中」机制，故按**路径 A**提交。
