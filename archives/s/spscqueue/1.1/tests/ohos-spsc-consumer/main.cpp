// main.cpp — 鸿蒙特有消费者测试：真实调用 spscqueue 的 SPSCQueue<T> 队列 API
// 运行于 OHOS 设备（aarch64-linux-ohos clang），退出码 0 表示全部断言通过。
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <thread>

#include <rigtorp/SPSCQueue.h>

int main() {
  using rigtorp::SPSCQueue;

  // 运行时断言 1: 基础 FIFO 语义 + capacity 下限修正
  {
    SPSCQueue<int> q(4);
    if (q.capacity() != 4) {
      std::fprintf(stderr, "capacity mismatch: %zu != 4\n", q.capacity());
      return 1;
    }
    if (!q.empty() || q.size() != 0) {
      std::fprintf(stderr, "new queue not empty\n");
      return 2;
    }
    for (int i = 0; i < 4; ++i) {
      q.push(i);
    }
    if (q.size() != 4 || q.front() == nullptr) {
      std::fprintf(stderr, "fill failed\n");
      return 3;
    }
    for (int expect = 0; expect < 4; ++expect) {
      if (q.front() == nullptr || *q.front() != expect) {
        std::fprintf(stderr, "FIFO order broken at %d\n", expect);
        return 4;
      }
      q.pop();
    }
    if (!q.empty()) {
      std::fprintf(stderr, "drain failed\n");
      return 5;
    }
  }

  // 运行时断言 2: 单生产者/单消费者多线程吞吐（OHOS 设备真实线程调度）
  {
    constexpr std::size_t kIter = 100000;
    SPSCQueue<std::size_t> q(kIter / 1000 + 1);
    std::atomic<bool> go(false);
    std::thread producer([&] {
      while (!go.load(std::memory_order_acquire)) {
      }
      for (std::size_t i = 0; i < kIter; ++i) {
        q.emplace(i);
      }
    });
    std::size_t sum = 0;
    go.store(true, std::memory_order_release);
    for (std::size_t i = 0; i < kIter; ++i) {
      while (q.front() == nullptr) {
      }
      sum += *q.front();
      q.pop();
    }
    producer.join();
    const std::size_t expect = kIter * (kIter - 1) / 2;
    if (sum != expect) {
      std::fprintf(stderr, "threaded sum mismatch: %zu != %zu\n", sum, expect);
      return 6;
    }
    if (q.front() != nullptr) {
      std::fprintf(stderr, "queue not drained\n");
      return 7;
    }
    std::printf("ohos-spsc-consumer: all assertions passed (iter=%zu)\n", kIter);
  }

  return 0;
}