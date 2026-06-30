# nsync

nsync 是 Google 开发的 C/C++ 同步原语库，提供跨平台的互斥锁（mutex）、条件变量（condition variable）、计数器、通知等同步机制。适用于多线程编程中的线程同步场景。

## 特性

- 提供 C 和 C++ 两套 API（`libnsync` 和 `libnsync_cpp`）
- 支持互斥锁（`nsync_mu`）、条件变量（`nsync_cv`）、计数器（`nsync_counter`）、通知（`nsync_note`）、一次性初始化（`nsync_once`）
- 基于 POSIX 线程实现，兼容 Linux 内核
- 零依赖，纯静态库

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.30.0](./1.30.0/) | published | 2026-06-01 |