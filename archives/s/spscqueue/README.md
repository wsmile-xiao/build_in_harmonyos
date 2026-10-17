# spscqueue

## 简介

spscqueue（rigtorp/SPSCQueue）是一个 C++11 实现的**单生产者单消费者（SPSC）无等待无锁固定容量队列**。
与 `boost::lockfree::spsc_queue` 和 `folly::ProducerConsumerQueue` 相比性能更高，
常用于低延迟流式处理与线程间高效通信。纯 header-only（CMake INTERFACE 库），无任何依赖。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 1.1 | built | 2026-09-02 |

## 依赖

- 无外部依赖（纯标准库：atomic / memory / new / type_traits）

## 编译说明

header-only 库，无需编译。Conan 配方仅安装 `include/rigtorp/SPSCQueue.h`：

```bash
# 验证（含 test_package 消费者验证）
conan create archives/s/spscqueue/1.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### HarmonyOS 平台适配

- 平台无关 C++11 代码，零修改适配（clang 15.0.4 / aarch64 实测通过）
- 上游测试 `SPSCQueueTest` ctest 1/1 通过；鸿蒙专项测试 `tests/ohos-spsc-consumer` 1/1 通过
- 单生产者单消费者多线程吞吐实测 96 ns/iter（10 万次迭代）