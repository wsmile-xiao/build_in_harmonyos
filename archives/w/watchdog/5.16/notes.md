# watchdog 5.16 — 适配笔记

## 构建信息

| 项目 | 值 |
|------|-----|
| 软件名 | watchdog |
| 版本 | 5.16 |
| 构建系统 | autotools |
| 源码地址 | https://downloads.sourceforge.net/project/watchdog/watchdog/5.16/watchdog-5.16.tar.gz |
| SHA256 | b8e7c070e1b72aee2663bdc13b5cc39f76c9232669cfbb1ac0adc7275a3b019d |
| 许可证 | GPL-2.0-or-later |

## 构建产物

| 二进制 | 安装路径 | 说明 |
|--------|---------|------|
| watchdog | sbin/ | 主看门狗守护进程 |
| wd_keepalive | sbin/ | 保活助手（watchdog 停止时使用） |
| wd_identify | sbin/ | 识别看门狗设备 |

另有 4 个 man 页面（man5/man8）和 1 个配置文件（watchdog.conf）。

## 适配问题与解决方案

### 问题1: HMDFS umask 077 临时目录权限问题

**现象**: configure 运行 config.status 时报错 "can't create ./confXXXXXX/subs1.awk: Permission denied"

**根因**: HMDFS FUSE 文件系统将文件所有权 remap 为 uid 20001006（file_manager），而当前进程以 uid 20020101 运行。config.status 使用 `umask 077` 创建临时目录，权限为 700（drwx------），由于所有权不是当前用户，导致无法访问。

**解决**: 在 configure 脚本中将 `umask 077` 改为 `umask 0`，使临时目录权限为 755（drwxr-xr-x），允许当前用户访问。

**补丁文件**: patches/0001-configure.patch

### 问题2: 编译警告（非致命）

**现象**: shutdown.c 中 `quotactl` 和 `reboot` 函数未声明

**根因**: OHOS 可能缺少 `<sys/quota.h>` 和 `<sys/reboot.h>` 头文件中的函数声明

**处理**: 警告不阻塞编译，链接成功。watchdog 的核心功能（监控、保活、识别）不受影响。reboot 和 quotactl 仅在系统关机/重启和磁盘配额场景使用。

## 测试

- `make check`: 无测试目标，返回 "Nothing to be done"
- test_package: 验证三个二进制文件已安装且可执行

## 依赖

无外部依赖。链接 `-lrt`（clock_gettime 在 glibc < 2.17 需要，OHOS 上可能不需要但无害）。
---

**编译结束**: 2026-09-04 05:44
**最终状态**: built
