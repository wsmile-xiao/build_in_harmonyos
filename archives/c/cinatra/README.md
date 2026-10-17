# cinatra

## 简介

cinatra 是 qicosmos（纯月科技）出品的 C++20 header-only HTTP 框架，基于 asio
与 async_simple 协程栈，提供 coro_http_server / coro_http_client、websocket、
restful 路由、multipart 上传下载、反向代理等能力。

- 上游：https://github.com/qicosmos/cinatra
- 许可证：Apache-2.0
- 依赖：无外部 conan 依赖（asio / async_simple / cmdline 均随包 vendored 部署）

## OHOS 适配

- 类型：header-only（0.8.9），仅部署 `include/` 头文件树
- 消费者需以 C++20 编译（协程）；clang 15 原生支持，gcc 需 `-fcoroutines`
- 平台差异：OHOS musl 无 `pthread_setaffinity_np`（glibc 专有），已用 POSIX
  `sched_setaffinity(0, ...)` 线程内绑定替代（patch 0001）
- OpenSSL（CINATRA_ENABLE_SSL）与 zlib（CINATRA_ENABLE_GZIP）为上游可选特性，
  默认关闭，未纳入包内依赖

## 已适配版本

| 版本 | 状态 |
|------|------|
| 0.8.9 | built（上游测试 95/95 通过，test_package 消费验证通过） |
