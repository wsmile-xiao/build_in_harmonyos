# SIGAR (System Information Gatherer And Reporter)

跨平台 C 库，用于获取操作系统与硬件级别的资源信息（CPU、内存、swap、磁盘、网络接口与连接、进程、uptime、load average、资源限制、文件系统等），并提供稳定 C API。核心库以 C 编写，官方仓库另有 Java/C#/Go/Perl/Ruby 等绑定。

## 功能概述

- 内存 / swap 用量（sigar_mem_get / sigar_swap_get）
- CPU 使用与信息（sigar_cpu_get / sigar_cpu_info_*）
- 磁盘 / 文件系统（sigar_file_system_* / sigar_disk_usage_get）
- 网络接口与连接（sigar_net_interface_* / sigar_net_connection_*）
- 进程信息（sigar_proc_*，list/stat/mem/time/state）
- 系统信息与 uptime / load average（sigar_sys_info_get / sigar_uptime_get / sigar_loadavg_get）
- 版本与资源限制（sigar_version_get / sigar_resource_limit_get）

## OHOS 适配

- **1.6.4 发布包无构建系统与测试套件**：该 tag（以及官方 SourceForge zip）只含 C 源码 + 头 + 绑定，构建脚手架与 13 个官方测试程序只存在于 hyperic/sigar 项目更晚的开发分支。本适配用手写 Makefile 构建 Linux 实现，并把官方 13 个测试程序原样 vendor 到 `tests/`，以 `make check` 在真机执行作为上游测试证据。
- 编译需 `-fgnu89-inline`（上游 `SIGAR_INLINE` 非 static inline 符号语义，现代编译器不再发射外部符号）+ `-D_GNU_SOURCE`。
- RPC 功能（`#include <rpc/rpc.h>`，供 NFS 探测）在 OHOS musl 上无 rpc/libtirpc，已编译排除（`SIGAR_NO_RPC` + 链接桩），`sigar_file_system_ping` 对 NFS 返回 SIGAR_OK。
- `major()/minor()` 需显式 `<sys/sysmacros.h>`。
- 库从 Linux `/proc`、`/sys` 读取指标（meminfo、stat、loadavg、uptime、partitions、diskstats、net 等），HarmonyOS Linux 内核均具备。

## 依赖关系

- 编译依赖：无（仅 libc + libm）。
- 运行依赖：无（纯静态链接）。

## 参考资料

- 官方仓库：https://github.com/hyperic/sigar
- 发布页：https://sourceforge.net/projects/sigar/
