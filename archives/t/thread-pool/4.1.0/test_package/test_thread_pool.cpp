// test_thread_pool.cpp — Substantive consumer test for thread-pool 4.1.0
// (Conan L1) — verifies the packaged BS::thread_pool v4.1.0 API from a
// downstream consumer: submit_task/future get, detach_loop + wait,
// submit_blocks via multi_future, the independent utilities header
// (BS::synced_stream), and the version macros, through a real threaded
// workload with a nonzero exit code on failure.

#include <BS_thread_pool.hpp>
#include <BS_thread_pool_utils.hpp>
#include <atomic>
#include <cstdio>

static int failures = 0;
#define CHECK(cond, label) do { \
    if (!(cond)) { std::fprintf(stderr, "FAIL: %s\n", label); failures++; } \
} while (0)

int main() {
    constexpr int N = 1000;
    BS::synced_stream sync(std::cerr);

    // 1) submit_task + future get
    BS::thread_pool pool;
    auto f = pool.submit_task([] { return 42; });
    CHECK(f.get() == 42, "submit_task/get returned expected value");

    // 2) detach_loop across many iterations, then wait
    std::atomic<int> counter{0};
    pool.detach_loop(0, N, [&counter](const int /*index*/) {
        counter.fetch_add(1, std::memory_order_relaxed);
    });
    pool.wait();
    CHECK(counter.load() == N, "detach_loop executed all iterations");

    // 3) submit_blocks returning multi_future; collect and sum block results
    constexpr int TOTAL = 100;
    auto mf = pool.submit_blocks(0, TOTAL,
        [](const int start, const int end) {
            int sum = 0;
            for (int i = start; i < end; ++i) sum += i;
            return sum;
        });
    mf.wait();
    int block_sum = 0;
    for (std::size_t i = 0; i < mf.size(); ++i) block_sum += mf[i].get();
    CHECK(block_sum == 4950, "submit_blocks sum of 0..99 == 4950");

    // 4) version macros match the packaged release
    CHECK(BS_THREAD_POOL_VERSION_MAJOR == 4, "version major == 4");
    CHECK(BS_THREAD_POOL_VERSION_MINOR == 1, "version minor == 1");
    CHECK(BS_THREAD_POOL_VERSION_PATCH == 0, "version patch == 0");

    if (failures == 0) {
        sync.println("PASS: BS::thread_pool 4.1.0 头文件库链接和核心 API 验证通过 (N=", N, ")");
        return 0;
    }
    return 1;
}
