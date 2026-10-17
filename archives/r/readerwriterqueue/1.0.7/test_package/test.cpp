// test_package 消费者测试：真实调用 readerwriterqueue 库 API（R34 反空壳）
#include <cassert>
#include <cstdio>
#include <thread>

#include "readerwriterqueue/readerwriterqueue.h"
#include "readerwriterqueue/readerwritercircularbuffer.h"

int main() {
    // 1. ReaderWriterQueue：enqueue/dequeue 往返
    moodycamel::ReaderWriterQueue<int> q(4);
    assert(q.enqueue(42));
    assert(q.enqueue(7));
    int val = 0;
    assert(q.try_dequeue(val) && val == 42);
    assert(q.try_dequeue(val) && val == 7);
    assert(!q.try_dequeue(val));

    // 2. 多线程 SPSC：生产者/消费者各 1000 条（真实并发语义验证）
    moodycamel::ReaderWriterQueue<int> q2(1024);
    std::thread producer([&]() {
        for (int i = 0; i < 1000; ++i) {
            while (!q2.enqueue(i)) { std::this_thread::yield(); }
        }
    });
    int received = 0;
    int sum = 0;
    while (received < 1000) {
        int v = 0;
        if (q2.try_dequeue(v)) {
            sum += v;
            ++received;
        }
    }
    producer.join();
    assert(received == 1000 && sum == 1000 * 999 / 2);

    // 3. BlockingReaderWriterCircularBuffer：定长环缓冲语义（满则 enqueue 失败）
    moodycamel::BlockingReaderWriterCircularBuffer<int> cb(4);
    for (int i = 0; i < 4; ++i) {
        assert(cb.try_enqueue(i));
    }
    // 缓冲区已满，下一次 try_enqueue 应失败
    assert(!cb.try_enqueue(99));
    int out = -1;
    assert(cb.try_dequeue(out) && out == 0);

    std::printf("test_readerwriterqueue 1.0.7: ALL ASSERTIONS PASSED\n");
    return 0;
}
