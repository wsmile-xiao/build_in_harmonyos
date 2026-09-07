# micro_inetd

## 简介

micro_inetd 是一个极简的网络服务派生器（simple network service spawner），由 Jef Poskanzer（ACME Labs）编写。它像 inetd 一样监听网络请求并为每个连接派生一个服务子进程，但只处理**一个端口和一个程序**。

典型用途：你有一个预期由 inetd 启动的服务程序（stdin/stdout 连接 socket 的 inetd 风格服务），但只想临时运行它，不想修改 `/etc/services` 和 `/etc/inetd.conf` 并重启 inetd——直接启动 micro_inetd，用完 Ctrl+C 即可。

## 功能与限制

- 用法：`micro_inetd <port> <program> [args...]`
- 每个接入连接 fork 一个子进程，把连接 socket dup2 到 stdin/stdout/stderr 后 execv 指定程序
- 仅实现 stream socket、nowait 模式，不做 user-id 切换
- IPv6 优先：若编译环境支持 `AF_INET6` + `IN6_IS_ADDR_V4MAPPED`，使用 v6 监听 socket（同时接受 v4 连接）
- SIGCHLD 处理器循环 waitpid 收割僵尸子进程
- 无守护进程化：前台运行，Ctrl+C 终止

## OHOS 适配

- 构建系统为纯 Makefile（单 C 文件，无 configure），通过 `CC=`/`CFLAGS=`/`LDFLAGS=` 命令行覆盖交叉编译
- 上游 Makefile 的 `install` 目标硬编码 `/usr/local/bin` 且无 `mkdir -p`，本配方不走上游 install，改用 conan `copy()` 直接安装产物（无需补丁）
- 上游 `LDFLAGS = -s`（链接期 strip）被命令行覆盖去掉，保留符号由发布流水线统一处理
- 依赖仅为系统 libc（musl），`readelf -d` 仅 NEEDED libc.so，无系统同名库风险（R26 不适用）
- 无源码补丁；`-ansi -pedantic -U__STRICT_ANSI__` 组合下 clang 15 交叉编译零警告

## 依赖关系

- 编译依赖：仅 OHOS SDK clang（无第三方库依赖）
- 运行依赖：仅系统 libc（musl）

## 参考资料

- 官方页面：https://www.acme.com/software/micro_inetd/
- 手册页：micro_inetd(1)（随包安装在 share/man/man1/）
- 上游作者：Jef Poskanzer <jef@mail.acme.com>，Copyright (C) 1996, 2000
