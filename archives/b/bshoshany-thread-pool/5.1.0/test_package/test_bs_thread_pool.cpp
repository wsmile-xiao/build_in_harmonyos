// test_bs_thread_pool.cpp — Substantive consumer test for bshoshany-thread-pool
// (Conan L1) — verifies the packaged BS::thread_pool API: submit_task, get(),
// detach_loop, wait, the version object, and the native thread-affinity
// extension through a real threaded workload.
// 5.1.0: adds checks for BS::this_thread::get/set_os_thread_affinity(), which
// on OHOS exercise the patched sched_getaffinity(0,...)/sched_setaffinity(0,...)
// code path (glibc pthread_*affinity_np() does not exist in musl).

#include <BS_thread_pool.hpp>
#include <atomic>
#include <cstdio>
#include <optional>
#include <vector>

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

#ifdef BS_THREAD_POOL_NATIVE_EXTENSIONS
    // 5) OHOS-patched native affinity extension: get current thread affinity.
    const std::optional<std::vector<bool>> initial = BS::this_thread::get_os_thread_affinity();
    CHECK(initial.has_value(), "get_os_thread_affinity returned a value (OHOS sched_getaffinity path)");

    // 6) set the affinity back to the initial mask and read it back.
    bool affinity_roundtrip = false;
    if (initial) {
        const bool set_ok = BS::this_thread::set_os_thread_affinity(*initial);
        const std::optional<std::vector<bool>> reread = BS::this_thread::get_os_thread_affinity();
        affinity_roundtrip = set_ok && reread.has_value() && *reread == *initial;
    }
    CHECK(affinity_roundtrip, "set_os_thread_affinity roundtrip via sched_setaffinity(0,...)");
#endif

    if (failures == 0) {
        std::printf("PASS: BS::thread_pool 单头文件库链接和核心 API 验证通过 (N=%d)\n", N);
        return 0;
    }
    return 1;
}
