// Consumer test for mpmcqueue 1.0 — exercises the actual MPMCQueue API.
// R02: 修复消费者提前退出竞态（有界队列 + 阻塞 push →
//      消费者见空即退后生产者永久阻塞挂起，CI #8531 复现）。
//      消费者改为按剩余计数耗尽退出；总量用原子变量断言（Release 下也真实执行）。
#include <atomic>
#include <cassert>
#include <thread>
#include <vector>

#include <rigtorp/MPMCQueue.h>

int main() {
  using rigtorp::MPMCQueue;

  // Basic enqueue/dequeue round-trip.
  {
    MPMCQueue<int> q(8);
    for (int i = 0; i < 8; ++i) {
      q.push(i);
    }
    for (int i = 0; i < 8; ++i) {
      int v = -1;
      q.pop(v);  // pop() 返回 void，显式调用（release 下也真实执行）
      assert(v == i);
    }
    assert(q.empty());
  }

  // Multi-producer / multi-consumer smoke test.
  {
    constexpr int kItems = 1000;
    constexpr int kProducers = 2;
    constexpr int kConsumers = 2;
    MPMCQueue<int> q(64);
    std::atomic<long> total{0};
    // 剩余待消费项数：消费者只在全部项消费完后退出，
    // 避免有界队列 + 阻塞 push 下消费者提前退出导致生产者永久阻塞（CI #8531 挂起）。
    std::atomic<int> remaining{kProducers * kItems};

    std::vector<std::thread> producers;
    for (int t = 0; t < kProducers; ++t) {
      producers.emplace_back([&q]() {
        for (int i = 0; i < kItems; ++i) {
          q.push(i);
        }
      });
    }
    std::vector<std::thread> consumers;
    for (int t = 0; t < kConsumers; ++t) {
      consumers.emplace_back([&q, &total, &remaining]() {
        int v;
        // try_pop 非阻塞拉取；队列瞬时为空时继续自旋等待生产者，
        // 直到剩余计数归零（生产者全部 push 完毕且全部被消费）。
        while (remaining.load(std::memory_order_relaxed) > 0) {
          if (q.try_pop(v)) {
            total.fetch_add(v, std::memory_order_relaxed);
            remaining.fetch_sub(1, std::memory_order_relaxed);
          }
        }
      });
    }
    for (auto &th : producers) {
      th.join();
    }
    for (auto &th : consumers) {
      th.join();
    }
    // 生产者 push 的 kProducers*kItems 个元素全部被消费，总量恰为
    // kProducers * (0+1+...+(kItems-1))。验证数据真实且完整流动。
    const long expected = kProducers * (kItems * (kItems - 1L) / 2L);
    assert(total.load() == expected);
    assert(remaining.load() == 0);
  }

  return 0;
}