# DRAFT-E577：OHOS 沙箱拦截 SysV IPC —— shmget/semget 触发 SIGSYS，改用 POSIX 共享内存与进程间信号量

> Contributor: buffer 1.19 适配任务 | Status: Draft | Updated: 2026-09-14
> Source: 任务卡 `buffer` 1.19（开源鸿蒙 PC 专项积分赛，分支 `feat/buffer-1.19`）
> 编号说明：初稿取号 E568，W4 独立审计指出 E568 已被主线 `DRAFT-E568-mdp-ohos-musl-terminfo-path` 占用，故换号为 **E577**（取号工具 `--check --fresh` 复核）。

## 背景

`buffer` 1.19（Lee McLoughlin，1990/1991）是一个重分块过滤器：父进程从 stdin 读入共享内存
环形缓冲，子进程把缓冲写到 stdout，用 System V 共享内存（`shmget`/`shmat`）+ System V
信号量（`semget`/`semop`/`semctl`）做互斥与流控。这类"双进程 + 共享内存环形缓冲"结构在
老工具里很常见（经典 afl 1.x 的覆盖率位图、各类 mailbox/工作队列实现）。

它在本设备（HarmonyOS PC / OHOS aarch64）上的失败形态非常具有误导性：

```text
$ printf 'x' | ./buffer
timeout: the monitored command dumped core          # 无任何 errno/权限类提示
$ ./probe shmget                                    # 10 行最小复现
Bad system call (core dumped)                       # signal 31 / exit 159
```

## 根因

OHOS 对应用/沙箱进程使用**白名单式 seccomp 策略**（`/proc/self/status` 实测
`Seccomp: 2`、`Seccomp_filters: 1`），System V IPC 的三个入口
`shmget`/`semget`/`msgget` 不在允许列表内，命中即由内核以 `SIGSYS` 终止进程。

关键区别（决定了排查方向）：

| | 普通"未实现/权限不足" | 本条目 |
|---|---|---|
| 返回 | `-1` + `errno`（ENOSYS/EPERM） | **不返回**，进程直接被信号杀死 |
| 现象 | `perror` 打出可读原因 | 只有 `Bad system call (core dumped)` |
| 按 errno 写的回退 | 生效 | **永不生效**（进程已死） |
| signal handler | 可捕获 | 本族 syscall 的 SIGSYS 通常不可恢复 |

旁证（本机实测）：

- `/proc/sys/kernel/shmall`、`shmmax` 可读，而 `sem`、`msgmax` 不存在；
- 最小复现程序（只调 `shmget(IPC_PRIVATE,4096,IPC_CREAT|0600)`）被杀；
  `python3 ctypes` 调 libc 的 `shmget` 同样被杀（说明与语言/运行时无关）；
- `fork`、`pipe`、`shm_open`+`ftruncate`+`mmap`、`mmap(MAP_SHARED|MAP_ANONYMOUS)`
  全部正常；
- 公开同型问题：OpenHarmony `third_party_musl` issue **I5MQ9A**
  「【OpenHarmony 3.2.6.2】【third_party 子系统】【TOD】【RK3568】【必现】shmget 接口报错
  signal 31, 程序退出」。

与既有条目的关系：

- **E051**（`setreuid`/`setregid` 的 SIGSYS 不可捕获）命中的是同一族现象，但它给出的方案是
  `#ifdef __OHOS__` 守卫 —— 该写法现在被 **R8 / `pre_push_check` PF5** 明令禁止
  （补丁新增行出现 `__OHOS__` 即拦），因此本条目补上"无平台宏"的等价路线。
- **E220** 建议"当真机证据证明 SIGSYS 时禁用误检的 IPC/SysV 运行时特性"，适用于 Perl
  `IPC::SysV` 这类**可选**特性；当 IPC 是程序主干（如 buffer/afl）时不能"禁用"，只能替换。
- **E246**（seccomp 拦 `adjtimex`）是同一 seccomp 白名单机制的另一个 syscall 家族。

## 修复方案（可移植替换，不含任何平台宏）

| 原语 | 替换为 |
|---|---|
| `shmget` + `shmat` | `shm_open(name, O_CREAT\|O_EXCL, 0600)` + `ftruncate(fd, size)` + `mmap(..., MAP_SHARED, fd, 0)`；或直接 `mmap(MAP_SHARED\|MAP_ANONYMOUS)`（fork 继承，无命名对象） |
| `shmdt` / `shmctl(IPC_RMID)` | `munmap` / `munmap` + `shm_unlink`（+ `close`） |
| `semget(IPC_PRIVATE, n, IPC_CREAT)` | `mmap(MAP_SHARED\|MAP_ANONYMOUS, n*sizeof(sem_t))` + 每个 `sem_init(&s[i], 1, 1)` |
| `semop(sem, -1)` / `semop(sem, +1)` | `sem_wait` / `sem_post`（0 时阻塞，语义一致） |
| `semctl(SETVAL, val)` | 在上锁前用 `sem_destroy` + `sem_init(&s, 1, val)` 重新初始化 |
| `semctl(IPC_RMID)` | `sem_destroy` + `munmap` |

要点与坑：

1. **信号量数组必须放在 `fork` 之前建立的共享映射里**（`pshared=1` 的 `sem_t` 只能活在
   进程间共享内存中）；父进程创建、子进程经 fork 继承，与原来 `semget` 后父子共用
   `semid` 的结构一一对应。
2. 段名要带 pid（`/buffer_<pid>`）以防并发实例冲突；**若沿用上游"先 detach、各进程再按
   名字 attach"的流程，就不能在首次 `mmap` 后立刻 `shm_unlink`**（子进程会 `ENOENT`）；
   只有改成 fork 继承同一映射时才可立即 unlink（可避免进程被 SIGKILL 时残留 `/dev/shm` 项）。
3. 不要给"失败回退"写基于 `errno` 的分支（见上表），进程在 syscall 处已经死了。
4. `-b 1` 这类上游固有死锁与 IPC 无关，替换后仍存在，不要误判为替换引入的回归。

## 证据（buffer 1.19 实测，2026-09-14）

| 项目 | 内容 |
|---|---|
| 原始失败 | 设备直接执行 `./buffer` → `Bad system call (core dumped)`（signal 31 / exit 159）；最小 `shmget` 探针同样被杀 |
| 修复方案 | `patches/0001-buffer.c.patch`（shm_open+ftruncate+mmap）、`patches/0002-sem.c.patch`（POSIX 进程间信号量） |
| 构建验证 | `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -c tools.build:jobs=1`（clang 15.0.4 / OHOS SDK 26.0.0.18）PASS |
| 上游测试 | N = 0（上游无测试套件；`prescan` `has_tests: false`）→ 0/0（不适用） |
| 消费者验证 | `test_package` 5/5 PASS（默认分块 256 KiB 往返、`-s/-b/-m` 1 MiB 往返、空输入、`-B` 末块补齐、`-i/-o` 文件模式），全部逐字节/sha256 断言 |
| 人工设备验证 | 30 MiB 随机数据 `cmp` 一致；12 个分块边界尺寸一致；并发 3 实例一致；连续 30 轮无残留 |
| 同族先例 | `archives/a/afl/1.35b` 补丁 0002-0004：`shmget/shmat → shm_open+ftruncate+mmap`（与 AFL++ `USEMMAP` 同源） |

推广价值：任何把 SysV 共享内存/信号量/消息队列当进程间通信主干的包（老式双进程过滤器、
多进程工作队列、共享位图统计、老数据库/编辑器/构建工具的 IPC）在 OHOS 上都会以同一种
"Bad system call" 形态失败；本条目给出可直接套用的等价替换表与三个坑。

## 关系

- 同族/相关：E051（SIGSYS 不可捕获，含已失效的 `__OHOS__` 方案）、E220（运行时特性误检
  需禁用）、E246（seccomp 拦 `adjtimex`）。
- 本条增量：**SysV IPC → POSIX 原语的完整映射表 + 白名单 seccomp 下"errno 回退永不生效"
  这一反直觉判据 + 命名段与 unlink 时序坑**，并给出两例已合入的落地实现。
