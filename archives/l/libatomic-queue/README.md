# libatomic-queue（atomic_queue）

> C++14 无锁（lock-free）并发队列库，header-only。

## 简介

atomic_queue 提供一组基于环形缓冲区与 `std::atomic` 的多生产者/多消费者无锁队列，
强调极少的原子操作、固定容量与值语义。核心容器是 header-only 类模板，无需编译即可使用：

```cpp
#include <atomic_queue/atomic_queue.h>
atomic_queue::AtomicQueueB2<int, std::allocator<int>> q(1024);
q.push(1);
int v = q.pop();
```

## OHOS 适配要点

- header-only：包内只安装 `include/atomic_queue/` 下的头文件（`atomic_queue.h`、
  `atomic_queue_mutex.h`、`barrier.h`、`defs.h`、`spinlock.h`），无 `.a`/`.so`。
- `defs.h` 原生支持 `__aarch64__`（`yield` 指令）；非 x86 下 `ATOMIC_QUEUE_FULL_THROTTLE`
  使用 atomic 而非 x86 汇编 barrier，aarch64 直接可用。
- 上游单元测试依赖 Boost.Test 与外部仓库（concurrentqueue / readerwriterqueue / xenium），
  CI 不可用；本包在 `test_package` 中用 13 项检查覆盖核心 API。
- CMake 目标：`atomic_queue::atomic_queue`。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| （无） | - | 仅 C++ 标准库（C++14） |

## 功能验证

```cpp
#include <atomic_queue/atomic_queue.h>
// FIFO、try_push/try_pop、RetryDecorator、move-only、多线程求和
```

## 参考

- [源码仓库](https://github.com/max0x7ba/atomic_queue)
- [上游 README](https://github.com/max0x7ba/atomic_queue/blob/master/README.md)
