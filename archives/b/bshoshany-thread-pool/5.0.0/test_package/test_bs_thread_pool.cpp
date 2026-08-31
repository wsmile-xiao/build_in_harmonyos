// test_bs_thread_pool.cpp — Substantive consumer test for bshoshany-thread-pool
// (Conan L1) — verifies the packaged BS::thread_pool API: submit_task, get(),
// detach_loop and wait through a real threaded workload.
// NOTE: v5.0.0 renamed parallelize_* -> submit_loop / detach_loop, and loop
// callbacks receive ONE argument (the index), not a [start, end) pair.

#include <BS_thread_pool.hpp>
#include <atomic>
#include <cstdio>

static int failures = 0;
#define CHECK(cond, label) do { \
    if (!(cond)) { std::fprintf(stderr, "FAIL: %s\n", label); failures++; } \
} while (0)

int main() {
    constexpr int N = 1000;

    // 1) submit_task + future get
    BS::thread_pool pool;
    auto f = pool.submit_task([] { return 42; });
    CHECK(f.get() == 42, "submit_task/get returned expected value");

    // 2) detach_loop across many blocks, then wait
    std::atomic<int> counter{0};
    pool.detach_loop(0, N, [&counter](const int /*index*/) {
        counter.fetch_add(1, std::memory_order_relaxed);
    });
    pool.wait();
    CHECK(counter.load() == N, "detach_loop executed all iterations");

    // 3) a second task verifying worker threads actually run in parallel
    auto g = pool.submit_task([] {
        int sum = 0;
        for (int i = 0; i < 100; ++i) sum += i;
        return sum;
    });
    CHECK(g.get() == 4950, "second submit_task sum of 0..99 == 4950");

    // 4) version object available
    CHECK(BS::thread_pool_version.major == 5, "thread_pool_version major == 5");

    if (failures == 0) {
        std::printf("PASS: BS::thread_pool 单头文件库链接和核心 API 验证通过 (N=%d)\n", N);
        return 0;
    }
    return 1;
}
