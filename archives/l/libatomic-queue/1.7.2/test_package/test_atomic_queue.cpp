// Consumer test for the header-only libatomic-queue package (v1.7.2).
#include <atomic_queue/atomic_queue.h>
#include <atomic_queue/barrier.h>

#include <atomic>
#include <cstdio>
#include <memory>
#include <thread>
#include <vector>

using namespace atomic_queue;

static int g_checks = 0;

#define CHECK(cond)                                                        \
    do {                                                                   \
        ++g_checks;                                                        \
        if (!(cond)) {                                                     \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            return 1;                                                      \
        }                                                                  \
    } while (0)

int main() {
    // 1) FIFO order + sum, single thread.
    {
        AtomicQueueB2<int, std::allocator<int>> q(1024);
        for (int i = 0; i < 100; ++i) q.push(i);
        CHECK(q.was_size() == 100);
        long sum = 0;
        for (int i = 0; i < 100; ++i) sum += q.pop();
        CHECK(sum == 4950);
        CHECK(q.was_empty());
    }

    // 2) try_push / try_pop / was_empty / was_full / capacity.
    {
        AtomicQueueB2<int, std::allocator<int>> q(8);
        int v = -1;
        CHECK(!q.try_pop(v));
        CHECK(q.was_empty());
        int pushed = 0;
        while (q.try_push(pushed)) ++pushed;
        CHECK(pushed > 0);
        CHECK(!q.try_push(-1));
        CHECK(q.was_size() == q.capacity());
        int out = -1;
        CHECK(q.try_pop(out));
        CHECK(out == 0);
    }

    // 3) RetryDecorator spins instead of failing.
    {
        RetryDecorator<AtomicQueueB2<int, std::allocator<int>>> q(64);
        q.push(7);
        CHECK(q.pop() == 7);
    }

    // 4) Move-only element type.
    {
        AtomicQueueB2<std::unique_ptr<int>, std::allocator<std::unique_ptr<int>>> q(64);
        q.push(std::make_unique<int>(42));
        auto p = q.pop();
        CHECK(p != nullptr && *p == 42);
    }

    // 5) MPMC stress: 3 producers / 3 consumers, sum integrity via a Barrier.
    {
        constexpr int PRODUCERS = 3, CONSUMERS = 3, COUNT = 10000;
        AtomicQueueB2<int, std::allocator<int>> q(1024);
        Barrier barrier;
        std::atomic<long> total{0};
        std::vector<std::thread> threads;
        for (int p = 0; p < PRODUCERS; ++p) {
            threads.emplace_back([&] {
                barrier.wait();
                for (int i = 0; i < COUNT; ++i) q.push(1);
            });
        }
        for (int c = 0; c < CONSUMERS; ++c) {
            threads.emplace_back([&] {
                barrier.wait();
                long s = 0;
                for (int i = 0; i < PRODUCERS * COUNT / CONSUMERS; ++i) s += q.pop();
                total.fetch_add(s, std::memory_order_relaxed);
            });
        }
        barrier.release(PRODUCERS + CONSUMERS);
        for (auto &t : threads) t.join();
        CHECK(total.load() == static_cast<long>(PRODUCERS) * COUNT);
    }

    std::printf("libatomic-queue consumer test PASS (%d checks)\n", g_checks);
    return 0;
}
