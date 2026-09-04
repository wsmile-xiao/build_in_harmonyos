// test_spscqueue.cpp — Conan L1 消费者验证：真实调用 spscqueue 的 SPSCQueue<T> API
// 运行于 OHOS 设备（aarch64-linux-ohos clang），退出码 0 表示全部断言通过。
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <thread>

#include <rigtorp/SPSCQueue.h>

int main() {
  using rigtorp::SPSCQueue;

  // 基础 FIFO 语义 + 容量修正（capacity<1 → 1）
  {
    SPSCQueue<int> q(4);
    if (q.capacity() != 4) {
      std::fprintf(stderr, "capacity mismatch: %zu != 4\n", q.capacity());
      return 1;
    }
    for (int i = 1; i <= 4; ++i) {
      q.push(i);
    }
    for (int expect = 1; expect <= 4; ++expect) {
      if (q.front() == nullptr || *q.front() != expect) {
        std::fprintf(stderr, "FIFO order broken at %d\n", expect);
        return 2;
      }
      q.pop();
    }
    if (!q.empty()) {
      std::fprintf(stderr, "drain failed\n");
      return 3;
    }
  }

  // 单生产者/单消费者多线程：真实调用 emplace/front/pop（header-only 库核心路径）
  {
    constexpr std::size_t kIter = 10000;
    SPSCQueue<std::size_t> q(kIter / 100 + 1);
    std::thread producer([&] {
      for (std::size_t i = 0; i < kIter; ++i) {
        q.emplace(i);
      }
    });
    std::size_t sum = 0;
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
      return 4;
    }
  }

  std::printf("test_spscqueue: OK\n");
  return 0;
}