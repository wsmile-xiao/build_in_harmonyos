# webdis

Webdis 是 Redis 的 HTTP/WebSocket 前端（作者 Nicolas Favre-Felix，BSD-2-Clause）：
把每一条 HTTP 请求的路径映射为一条 Redis 命令，把 Redis 的回复渲染成 JSON、raw 文本、
MessagePack 或自定义分隔格式；同时支持把连接升级为 WebSocket，用帧收发同一套命令。

## 功能概述

- **HTTP → Redis 直通**：`GET /SET/key/value`、`GET /GET/key`、`GET /INCR/counter` …
  返回 `{"SET":[true,"OK"]}`、`{"GET":"value"}`、`{"INCR":1}` 等 JSON 结构
- **多种输出格式**：默认 JSON；`/GET/key.raw` 原始文本；`/GET/key.msg` MessagePack；
  `?format=custom&separator=…` 自定义分隔；`?jsonp=cb` JSONP
- **WebSocket 通道**：`ws://host:port/.json`（或 `.raw`/`.msg`），帧内容即命令，
  支持 SUBSCRIBE/PUBLISH 等流式命令
- **连接池与多线程**：`threads` 个 libevent 事件循环线程，每线程 `pool_size` 个 Redis 连接
- **ACL**：可按命令启用/禁用，支持 HTTP Basic Auth 兜底
- **附带的 `hiredis` 适配层**：0.1.22 的 tarball 直接 vendored hiredis/jansson/http-parser，
  编译时无需外部安装这些头文件与库

## OHOS 适配

- 构建系统为**上游手写 Makefile**（`make` 直接产出可执行文件 `webdis`），**源码零补丁**。
- 唯一的外部链接依赖是 **libevent**（另可选 MessagePack）：`libevent/2.1.13` 取自制品仓预编译包，
  MessagePack 通过 `msgpack-c/7.0.1`（静态）接入 —— 与上游 CI 安装 `libevent-dev libmsgpack-dev`
  的参考构建保持一致。
- 两个必须显式处理的构建参数：
  1. 上游 Makefile 以 `CFLAGS ?=` 定义默认编译参数；Conan 构建环境已导出 `CFLAGS`，
     `?=` 不会生效，若不显式传入上游默认值会因 `-Isrc` 丢失而报 `hiredis/async.h file not found`。
  2. MessagePack 的自动探测依赖 `/usr/lib/libmsgpack*.so`；显式启用时还需把
     `src/formats/msgpack.o` 加入 `FORMAT_OBJS`，否则链接报 `undefined symbol: msgpack_reply`。
- 实测平台行为正常：libevent 事件循环、多线程连接池、并发 20 请求、WebSocket 升级、
  大 URL/大上传限流、ACL 403、`$TMPDIR` 日志落盘、SIGTERM 退出；产物为 ELF64 AArch64 PIE，
  链接 OHOS musl 与 libevent.so，不含宿主构建路径。
- `test_package/test_webdis_ohos.sh` 为鸿蒙特有测试：ELF64/AArch64/PIE/musl/NX/无路径泄漏校验，
  加上与真实 `redis-server` 的端到端层（SET/GET/INCR、错误透传、ACL、MessagePack、20 并发、WebSocket 101）。

## 依赖关系

- 编译依赖：`libevent/2.1.13`、`msgpack-c/7.0.1`（hiredis/jansson/http-parser 已随上游源码 vendored）
- 运行依赖：**Redis 服务端**（webdis 是其 HTTP 前端，自身不存储数据）+ 运行期 `libevent.so`

## 参考资料

- 上游官网/文档：<https://webdis.io/>（源码仓库 <https://github.com/nicolasff/webdis>）
- 源码包：`0.1.22.tar.gz`（sha256 `4ee465f85999aeba3743a8ed6c7d79690bffe7a8ffb6c7ddec1d4bb6bd1d8685`）
- 适配验证报告：`0.1.22/reports/test-report.md`
