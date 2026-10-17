# buffer

`buffer` 是一个极快的重分块（reblocking）过滤器：它把两个进程用一段共享内存环形缓冲连接起来，
一个进程只负责从 stdin 读并填充缓冲，另一个进程只负责把缓冲写到 stdout，从而让写入侧始终处于
紧凑的写循环中、不必等待读侧——原作者（Lee McLoughlin，Imperial College）用它把 `tar` 归档
写到远程磁带机的速度提高了约 5 倍。

## 功能概述

- stdin → 共享内存环形缓冲 → stdout 的流水线式转发，可按块大小/块数/共享内存上限调参
- 支持自定义块大小（`-s`）、块数（`-b`）、总共享内存（`-m`）、写出比例（`-p`）、写前暂停（`-u`）
- `-B` 把末块补齐到块大小（部分磁带/盒式驱动器需要）
- `-i` / `-o` 直接指定输入/输出文件；`-t` 打印吞吐；`-z` 调整告警阈值
- 输入输出严格字节保真：除 `-B` 的末块补齐外，输出与输入逐字节一致

## OHOS 适配

- **核心适配点**：上游整体建立在 System V IPC 之上（`shmget`/`shmat` 共享内存 +
  `semget`/`semop`/`semctl` 信号量）。OHOS 沙箱拦截 SysV IPC，内核直接以
  `SIGSYS`（signal 31，进程 exit 159）终止调用进程，工具在任何数据通路开始前就崩溃。
- 两个补丁把 IPC 层换成 POSIX 原语（不引入任何平台宏，Linux 上同样可编译运行）：
  - `0001-buffer.c.patch`：`shmget`/`shmat`/`shmdt`/`shmctl(IPC_RMID)` →
    `shm_open` + `ftruncate` + `mmap(MAP_SHARED)` + `shm_unlink`；
    同时删除与现代 `sys/shm.h` 原型冲突的 K&R `extern char *shmat();` 声明。
  - `0002-sem.c.patch`：SysV 信号量 → POSIX 进程间信号量（`sem_t` 数组放在
    `fork` 之前创建的 `MAP_SHARED|MAP_ANONYMOUS` 映射中，父子进程共享同一段物理内存）。
- 同类先例：`archives/a/afl/1.35b` 的 `shmget → shm_open+mmap` 补丁（与 AFL++ 的
  `USEMMAP` 方案同源）。
- 已知限制：`-b 1` 会死锁（可用块初始为 `blocks-1 = 0`，写侧永远等不到空块）——
  这是上游设计固有行为，与本次适配无关。

## 依赖关系

- 编译依赖：无（仅需要 C 编译器与 make；raw Makefile，无 configure/CMake）
- 运行依赖：libc（POSIX 共享内存与进程间信号量）

## 参考资料

- 上游项目主页：http://hello-penguin.com/software/buffer （**已不可达**：DNS 可解析但 TCP 无响应）
- 手册页：`man buffer`（源码树内 `buffer.man`）
- Debian 源包：https://packages.debian.org/source/sid/buffer
- 源码获取：Fedora dist-git 官方 lookaside 缓存中的 `buffer-1.19.tar.gz`
  （与 Debian `1.19-12.1` 的 `orig.tar.gz` 逐文件 sha256 一致）
