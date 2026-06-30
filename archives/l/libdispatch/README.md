# libdispatch

Grand Central Dispatch (GCD) 开源实现，Apple 的并发编程框架。

## 描述

libdispatch 是 Apple GCD (Grand Central Dispatch) 的核心用户空间库开源实现。
提供全面的并发代码执行支持，包括：
- 异步任务调度 (dispatch_async/dispatch_sync)
- 队列管理 (serial/concurrent queues)
- 定时器调度 (dispatch_after/dispatch_source)
- 信号量 (dispatch_semaphore)
- 组调度 (dispatch_group)
- I/O 多路复用 (dispatch_io)
- 数据缓冲 (dispatch_data)

## 依赖

- clang 3.8+ (需要 -fblocks 支持)
- cmake 3.15+
- pthread

## 编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 5.10.1 | published | 2026-06-02 |

## 特殊说明

- 需要 `-fblocks` 编译选项（clang Blocks 特性）
- 在 OpenHarmony 上需要 `-D__OHOS__` 编译标志启用平台适配
- 无可执行文件（纯库项目）
- 包含 BlocksRuntime (Apple Blocks 语言特性的运行时库)
