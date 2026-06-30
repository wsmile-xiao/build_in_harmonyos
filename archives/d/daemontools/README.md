# daemontools

UNIX 服务管理工具集

## 简介

daemontools 是 Daniel J. Bernstein 开发的 UNIX 服务监管工具集，提供服务启动、监控、日志记录和进程管理功能。

## 核心工具

| 工具 | 功能说明 |
|------|----------|
| supervise | 监控并自动重启服务进程 |
| svscan | 启动并监管一组 supervise 进程 |
| svscanboot | svscan 的启动脚本 |
| svc | 向被监管的服务发送控制信号 |
| svok | 检查 supervise 是否在运行 |
| svstat | 报告被监管服务的状态 |
| multilog | 读取和过滤日志，自动轮转 |
| tai64n | 为日志行添加 TAI64N 时间戳 |
| tai64nlocal | 将 TAI64N 时间戳转换为本地时间 |
| setuidgid | 以指定 UID/GID 运行程序 |
| envdir | 从目录文件设置环境变量 |
| envuidgid | 从 UID/GID 设置环境变量 |
| fghack | 阻止守护进程控制前台状态 |
| pgrphack | 阻止守护进程获取新进程组 |
| setlock | 加锁文件并运行程序 |
| softlimit | 设置资源限制并运行程序 |
| readproctitle | 从 /proc 显示进程标题 |

## 版本 0.76

- **状态**: 已发布（为 OpenHarmony aarch64 编译）
- **编译日期**: 2026-06-11
- **编译器**: clang 15.0.4
- **构建系统**: DJB 风格（自定义 Makefile + try-compile 检测）

## OpenHarmony 平台适配说明

- `extern int errno;` 声明与 musl libc 的 errno 宏冲突 → 已修复为 `#include <errno.h>`
- 编译器/链接器从 gcc 替换为 clang（conf-cc, conf-ld, find-systype.sh）
- DJB 测试套中 FIFO/supervise 测试在 OpenHarmony 上受限 → 已跳过
- DJB 构建系统不支持 `make install DESTDIR=` → 使用手动安装
- K&R 风格 C 代码的编译警告为预期行为（2001 年代代码风格）

## 知识图谱

- **E999**: DJB errno extern 与 musl errno macro 冲突修复模式（适用于 qmail, djbdns, ucspi-tcp 等所有 DJB 软件）

## 主页

https://cr.yp.to/daemontools.html