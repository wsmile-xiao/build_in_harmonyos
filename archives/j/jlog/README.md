# JLog

JLog (libjlog) 是一个纯 C 实现的持久化消息队列（durable message queue），支持多个订阅者（subscriber）与发布者（publisher）并发读写日志消息，线程安全且多进程安全。发布者写入固定大小的日志缓冲（segment），订阅者消费消息；缓冲写满后自动轮转，并在无消费者挂起时清理旧缓冲。

## 功能概述

- 纯 C、极小的 API 与实现，无重量级依赖
- 多发布者 / 多订阅者并发安全（pthread 互斥）
- 磁盘持久化（segment + index + checkpoint + metastore 结构）
- 可选 LZ4 压缩（未检测到 lz4.h 时自动使用 null 压缩提供者）
- 提供 jlogctl / jlogtail 管理工具与 shell 辅助脚本

## OHOS 适配

- 源码包不携带预生成的 `configure`，仅有 `configure.in`；构建前需用 `autoconf` 生成（配方以 `tool_requires("autoconf/2.72")` 保证）
- 以 `--build/--host=aarch64-unknown-linux-gnu` 显式标注，configure 的 `case $host` 落入 `*linux*` 分支（`-D_GNU_SOURCE` 等），无需改平台判定
- `configure.in` 对 GCC/Clang 追加 `-Werror`；2008 年代码在现代 clang 下会产生告警即失败，已 patch 去除 `-Werror`
- 本适配构建静态库 `libjlog.a` 并发布头文件（纯库，非命令行工具包）

## 依赖关系

- 构建期：`autoconf`（生成 configure）；LZ4 可选（未显式 require，缺省 null 压缩）
- 运行期：libc / pthread（OHOS musl 内含）

## 参考资料

- 官网：https://labs.omniti.com/labs/jlog
- 源码仓库：https://github.com/omniti-labs/jlog
