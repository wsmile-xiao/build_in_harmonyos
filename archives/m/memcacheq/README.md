# MemcacheQ

> 基于 memcache 协议的持久化 FIFO 消息队列守护进程

## 简介

MemcacheQ（Steve Chu）是一个简单、快速、可靠的消息队列服务：对外讲 memcache
文本协议（TCP，默认端口 22201），内部用 libevent 做事件循环、BerkeleyDB 做
持久层。核心语义是**每个 key 一条独立 FIFO 队列**：`set` 入队（回 `STORED`），
`get` 出队（出队即消费、即删），消息落盘于 `-H` 指定的 BDB 环境，重启不丢。
上游 2008 年发布 0.2.1 后停止维护，官方站点为 Google Code 存档。

## 功能概述

- memcache 文本协议：`set` 入队、`get` 出队、`delete`、`stats` / `stats queue` /
  `stats reset`、`version`、`quit`
- 每个 key 一条独立 FIFO 队列，队列间相互隔离
- BerkeleyDB 持久化，守护进程重启后队列内容仍在
- 多线程事件循环（`--enable-threads`）
- CLI：`-p`/`-U`/`-l` 网络参数、`-H` dbhome、`-N`/`-R`/`-T` 队列参数、
  `-v`/`-vv` 日志、`-h` usage、`-i` license

## OHOS 适配

跨版本通用要点（版本级细节见 `0.2.1/notes.md`）：

- 上游 tarball 无 config.guess/config.sub、无 AC_CANONICAL_HOST，工具链完全
  通过 Conan profile 的 CC/CFLAGS 进入，无需平台三元组补丁。
- configure 及其生成的 config.status 以 `umask 077 && mktemp` 建临时目录，
  在 HMDFS 上属主自己都不可写，需改 umask 并把临时目录重定向到构建目录内。
- `hashtable.h` 的 `extern inline` 是 GNU89 语义，`cppstd=gnu20` 下需
  `-fgnu89-inline`（零源码补丁）。
- 产物刻意不带 RPATH（HNP 加固基线），musl loader 靠 `LD_LIBRARY_PATH` 找
  libevent/libdb，由配方 `runenv_info` 传递。
- 守护进程需可写的 dbhome 目录方可启动。

## 依赖关系

- 编译/运行依赖：`libevent`（事件循环）、`db`（BerkeleyDB 6.2，持久层），
  均为共享库。
- 无其他外部依赖。

## 验证口径

上游无测试套件（tarball 逐项审计见 `0.2.1/notes.md`）。适配验证由
test_package 补全：功能 15/15（F1–F13b，真守护进程协议测试）+ 鸿蒙特有
7/7（A1–A7，ELF/ABI 检查）= 22/22。

## 参考资料

- 上游（Google Code 存档）：<https://memcacheq.googlecode.com/>
- 源码 tarball（MacPorts distfiles 权威镜像）：
  <https://distfiles.macports.org/memcacheq/memcacheq-0.2.1.tar.gz>
- 同协议近亲 memcached：<https://memcached.org>
- 本包适配笔记：`0.2.1/notes.md`；编译元数据：`0.2.1/manifest.yaml`
