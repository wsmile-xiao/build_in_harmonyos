# ivykis

## 软件简介

ivykis 是一个异步 I/O 库，专为 Linux 系统设计，提供高效的异步事件处理能力。

**主要特性**：
- 基于 epoll/kqueue 的事件循环
- 定时器管理
- 信号处理
- 线程支持

## 版本历史

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 0.43.2 | published | 2026-05-29 |

## 鸿蒙适配

- HMDFS workaround: E011/E080
- musl pthread_cancel stub: E085
- 功能验证通过 ✅