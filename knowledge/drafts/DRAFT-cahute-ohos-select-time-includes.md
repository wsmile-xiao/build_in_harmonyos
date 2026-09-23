# DRAFT-cahute-ohos-select-time-includes — OHOS 上 select()/fd_set 需显式包含 <sys/select.h> 与 <sys/time.h>

> **Contributor**: pc1-11 | **Status**: DRAFT | **Updated**: 2026-09-06
> **Severity**: medium | **Category**: headers / posix / ohos / compat / libc
> **Audience**: 任何在 OHOS 上使用 select()/FD_* 宏/struct timeval 的 C/C++ 三方库
> **Stem**: DRAFT-cahute-ohos-select-time-includes（与同名 .kv 配对，字段逐一对齐）

## 问题（Symptom）

cahute 0.6 在 OHOS aarch64 上用 CMake/Ninja 编译 `lib/linkmedium.c`（`CAHUTE_LINK_MEDIUM_POSIX_SERIAL` 路径使用 `select()`/`FD_SET`）时报：

```text
lib/linkmedium.c:164:17: error: use of undeclared identifier 'fd_set'
lib/linkmedium.c:165:32: error: variable has incomplete type 'struct timeval'
```

上游源码仅依赖 `internals.h`（包含 `<time.h>`、`<unistd.h>`、`<sys/ioctl.h>`、`<termios.h>` 等）间接提供这些类型；在 Linux/glibc 上传递包含正常，OHOS 上不成立。

## 根因（Root Cause）

OHOS（musl 系 libc）不会通过 `<time.h>`/`<unistd.h>`/`<termios.h>` 传递引入 `fd_set`/`struct timeval`；`select()` 系列类型必须来自 `<sys/select.h>`（`fd_set`、`FD_*`、`select()`）与 `<sys/time.h>`（`struct timeval`）。上游未显式包含，属于平台头文件传递性差异。

## 方案（Solution）

非 WIN32 分支显式包含两个头（普适 POSIX 守卫，不引入平台宏）；同一根因下 bossa 1.9.1 已有完全同构补丁 `0001-src-PosixSerialPort-missing-includes.patch`（`+#include <sys/select.h>` + `+#include <sys/time.h>`），证明跨库可复用。

```c
#include "internals.h"
#if WIN32_ENABLED
# include <ntddscsi.h>
#endif

#if defined(__linux__) && HAVE_LINUX_SERIAL_H
# include <linux/serial.h>
#endif

#if !WIN32_ENABLED
# include <sys/select.h>
# include <sys/time.h>
#endif
```

## 验证（Verification）

- 补丁后 `cmake --build` 退出码 0，`libcahute.a` 生成；
- CLI `p7 --version`、`xfer9860 -h` 冒烟退出码 0；
- 全部证据见 cahute r01/r02 的 `r01-source-audit.log`、`r02-baseline-isolation-audit.log` 及 conan create 日志（test_package 1/1 Passed）。

## 适用边界与反例

- 适用：任何在 OHOS 上使用 `select()` / `FD_*` / `struct timeval` 的 C/C++ 库（串口、套接字、管道轮询路径）。
- 反例：仅用 `usleep()`/`nanosleep()` 或纯同步 I/O 的库不需要；Windows 路径由 `WIN32_ENABLED` 守卫排除。
- 不适用平台宏：非 WIN32 守卫是平台无关 POSIX 修复，不属于 `__OHOS__` 平台宏，符合 R8 例外口径（libc 探针/头文件兼容类）。

## 查重差异（相对既有知识）

| 轴 | 结论 |
|---|---|
| exact_duplicate | false（E235=OpenSSL 熵源、E309=生成公共头、E164=adjtimex、E102=mmsg/recvmmsg 均不同根因） |
| causal_duplicate | false（无同因果条目） |
| trigger_overlap | false（引擎按关键字粗筛命中 E102，但 mmsg 属 musl 批量消息缺失，与 select 头文件传递性无关） |
| solution_overlap | false（无既有条目提供 include 修复方案） |
| combination_novelty | true（OHOS + POSIX select 头文件 组合未覆盖） |
| boundary_novelty | true（非 WIN32 守卫 + 双头 include 的边界形态新增） |
| test_migration_novelty | false |

**路径决定：new_draft**（C1 已验证、可跨库复用、四范围查重未命中且存在新增差异 → 路径 B）。