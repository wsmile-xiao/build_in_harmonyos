# pkill

pkill 是 procps-ng 套件中的进程管理工具，用于按进程名发送信号（如终止、挂起等）。它从 `src/pgrep.c` 编译而来，与 pgrep 共享同一源文件，链接 libproc2 库。

## 功能概述

- 按进程名（正则匹配）发送信号
- 支持所有标准 POSIX 信号
- 可配合 pgrep 使用进行进程查找

## OHOS 适配

- **构建系统**: autotools config.status 在 HMDFS 上失败，改用手动编译
- **musl 兼容**: `__fpending` 宏在 musl libc 下不可用，通过补丁修复
- **头文件缺失**: `sort.h` 缺少 `#include <stddef.h>`，musl 下 `size_t` 未定义
- **syscall 限制**: `library/meminfo.c` 和 `vmstat.c` 使用 `hsearch_data`（musl 不支持），编译时跳过
- **静态链接**: 终端工具静态链接 (R26)，避免系统库污染

## 依赖关系

- 无编译依赖（源码内嵌 libproc2）
- 无运行依赖（静态链接）

## 参考资料

- 上游源码: https://gitlab.com/procps-ng/procps
- 发布包: https://sourceforge.net/projects/procps-ng/files/Production/
