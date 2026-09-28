# postmark

## 简介

postmark 是 NetApp 开发的经典文件系统基准测试工具（Jeffrey Katcher，1997-2001）。
它模拟小文件密集型工作负载（如电子邮件/新闻服务器的元数据与数据操作）：
同时维护多组小文件，执行创建、读取、追加、删除等事务，输出吞吐量（事务/秒）
与 I/O 延迟报告，广泛用于磁盘与文件系统性能评测。

## OHOS 适配

### 1.53

- 纯 Makefile 构建（单文件 C：postmark-1.53.c），`make CC=clang -j1 postmark`
- 关键修复：`getwd()` 为废弃 POSIX API，OHOS bionic libc 无此符号 → 改用标准
  `getcwd(x,MAX_LINE)`（与 `#ifdef _WIN32` 分支一致），补充 `#include <unistd.h>`
- 上游官方 SLAC 网页源已从互联网消失，采用 Debian 权威快照源
  （snapshot.debian.org orig tarball，sha256 已实测固化）
- 上游无测试套件（无 tests/ 目录、Makefile 无 check 目标），由 test_package
  端到端 benchmark 验证（4 项断言，100% 通过）
- License: Artistic License（源码内含全文）
