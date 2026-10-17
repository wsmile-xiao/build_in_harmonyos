# DRAFT: SysV IPC（shmget/shmat）编译链接可用但运行期被 OHOS PC 内核 SIGSYS(31) 拦截

- **草稿 ID**: DRAFT-wmget-0.6.1-sysv-shm-sigsys-seccomp
- **来源库**: wmget 0.6.1（OHOS PC aarch64, clang 15.0.4 / OHOS SDK 26.0.0.18）
- **状态**: 草稿（待主编 promote 为正式 E 条目）

## 问题（三层，真机实测）

wmget 的 dock 服务器模式（`wmget dock`）用 SysV 共享内存共享下载任务队列：
`server.c: init_shmem()` 调 `shmget(IPC_PRIVATE, sizeof *shmem, SHM_R|SHM_W)` +
`shmat()`，fork 出的下载 worker 与客户端状态读取都走这块共享内存。在 OHOS PC
真机上是**"编译全绿、运行即死"**：

1. **头文件/符号层（编译链接通过）**：OHOS sysroot 自带 `<sys/shm.h>`，libc 导出
   `shmget/shmat/shmctl`；wmget 13 个 .c 一体直编零告警，链接成功。任何
   configure/CMake 式的能力探测（头文件存在 + 链接成功 + 能生成可执行文件）
   都判定"SysV shm 可用"。

2. **运行期（SIGSYS 即死）**：进程一执行 `shmget` 系统调用立即被内核杀死——

   ```
   $ ./shmtest        # shmget(IPC_PRIVATE,4096,IPC_CREAT|0600) → shmctl(RMID)
   Signal 31 (core dumped)
   $ echo $?
   159                 # = 128 + 31 (SIGSYS "Bad system call")
   ```

   稳定复现，无任何 errno 机会（用户态错误分支来不及执行，`error_sys()` 这类
   兜底日志一行都不会打出）。稳定复现的最小探针与完整证据见
   `notes.md`「平台事实」节。

3. **对照组（POSIX 面可用）**：同机同编译器，POSIX 共享内存完全正常——

   ```c
   int fd = shm_open("/wmget_probe", O_CREAT|O_RDWR, 0600);  /* fd=3, rc=0 */
   shm_unlink("/wmget_probe");
   ```

   即拦截面精确针对 SysV IPC 系统调用族（shmget/semget/msgget 一类），
   POSIX 命名共享内存不在其内。

## 根因

OHOS PC 内核/安全策略在运行期拦截 SysV IPC 系统调用（SIGSYS = seccomp 类
"bad system call"），与编译期可见性完全脱节：sysroot 有头文件、libc 有符号、
编译器无告警——**编译期能力检测 ≠ 运行期可用性**。这与既有知识
E220（perl metaconfig 的 IPC/SysV 探测）、E022（POSIX 信号量运行期面）同族
但层级不同：本条是 C 程序 SysV shm 运行期 SIGSYS 的直接证据条目。

## 影响面

- 所有运行期用 SysV IPC 的 C/C++ 程序（DockApp 后台队列、多进程共享统计、
  System V 信号量互斥、老式消息队列）在 OHOS PC 上运行即崩。
- wmget 具体表现：`wmget dock`（X11 面板服务器）启动即 SIGSYS；CLI 子命令
  （request/list/cancel/--help/--version）不触碰 shm，不受影响。

## 推荐方案（优先级 1）：替换为 POSIX 面 / 通用原语

- 共享队列：`shm_open` + `ftruncate` + `mmap(MAP_SHARED)`（同机实测可用），或
  fork 前匿名 `mmap(NULL, len, PROT_READ|PROT_WRITE, MAP_SHARED|MAP_ANONYMOUS, -1, 0)`；
- System V 信号量 → 事件驱动（poll/eventfd）或 POSIX 命名信号量；
- 保持源码平台中立（不引平台宏）；注意少数平台 `shm_open` 需 `-lrt`。

无法改源码时：如实把该运行面申报为平台受限（无头验证收缩到 CLI 契约 +
产物 ELF/链接层），**禁止伪造运行证据**。

## 验证方式

最小探针编译运行即判：`shmget` 探针 rc=159/SIGSYS = 平台拦截存在；
`shm_open` 探针 rc=0 = POSIX 面可用。修复后复跑原程序的真实 SysV 调用路径。

## 元数据

- 触发任务：wmget 0.6.1 适配（OHOS PC, HarmonyOS）
- 证据：`shmtest.c`（SIGSYS, rc=159）、`posshmtest.c`（rc=0），均在
  2026-09-27 真机（aarch64, 8 核 / 31G）实测
- 作者：主理-73
