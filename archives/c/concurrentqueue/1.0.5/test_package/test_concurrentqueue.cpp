// test_concurrentqueue.cpp — L1 smoke test for concurrentqueue 1.0.5 header-only library
// 验证 moodycamel/concurrentqueue.h 可正常包含，并验证入队/出队与多线程生产者-消费者
#include "moodycamel/concurrentqueue.h"
#include <iostream>
#include <thread>
#include <atomic>

int main() {
    // 测试 1: 单线程 enqueue / try_dequeue
    moodycamel::ConcurrentQueue<int> q;
    for (int i = 0; i < 1000; ++i) {
        q.enqueue(i);
    }
    int item = -1;
    int count = 0;
    while (q.try_dequeue(item)) {
        ++count;
    }
    if (count != 1000) {
        std::cerr << "FAIL: expected 1000 dequeued items, got " << count << std::endl;
        return 1;
    }

    // 测试 2: 多线程生产者-消费者
    moodycamel::ConcurrentQueue<int> q2;
    std::atomic<int> consumed{0};
    constexpr int N = 10000;

    std::thread producer([&]() {
        for (int i = 0; i < N; ++i) {
            q2.enqueue(i);
        }
    });
    std::thread consumer([&]() {
        int v = -1;
        while (consumed.load() < N) {
            if (q2.try_dequeue(v)) {
                ++consumed;
            }
        }
    });
    producer.join();
    consumer.join();
    if (consumed.load() != N) {
        std::cerr << "FAIL: multi-thread expected " << N << " consumed, got " << consumed.load() << std::endl;
        return 1;
    }

    std::cout << "PASS: concurrentqueue 头文件库链接和核心 API 验证通过" << std::endl;
    return 0;
}
