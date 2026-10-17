// test_asyncplusplus.cpp — L1 consumer test for async++ 1.2
//
// R34: substantive test that actually exercises the library API:
//   1. Task creation and execution via async::spawn
//   2. Task continuation via .then()
//   3. parallel_for over a range
//   4. parallel_invoke of multiple callables

#include <async++.h>

#include <atomic>
#include <cstdio>
#include <vector>

// Test 1: basic task spawn and wait
static int test_task_spawn() {
    auto task = async::spawn([] {
        return 42;
    });
    int result = task.get();
    if (result != 42) {
        std::fprintf(stderr, "FAIL: task_spawn returned %d, expected 42\n", result);
        return 1;
    }
    std::printf("  PASS: task_spawn\n");
    return 0;
}

// Test 2: task continuation (.then())
static int test_continuation() {
    auto task = async::spawn([] {
        return 10;
    }).then([](int val) {
        return val * 3;
    });
    int result = task.get();
    if (result != 30) {
        std::fprintf(stderr, "FAIL: continuation returned %d, expected 30\n", result);
        return 1;
    }
    std::printf("  PASS: continuation\n");
    return 0;
}

// Test 3: parallel_for
static int test_parallel_for() {
    std::vector<int> data(100, 0);
    std::atomic<int> sum{0};
    async::parallel_for(data, [&](int& elem) {
        elem = 1;
        sum.fetch_add(1, std::memory_order_relaxed);
    });
    if (sum.load() != 100) {
        std::fprintf(stderr, "FAIL: parallel_for processed %d items, expected 100\n",
                     sum.load());
        return 1;
    }
    // Verify all elements were set
    for (size_t i = 0; i < data.size(); ++i) {
        if (data[i] != 1) {
            std::fprintf(stderr, "FAIL: parallel_for data[%zu] = %d, expected 1\n", i, data[i]);
            return 1;
        }
    }
    std::printf("  PASS: parallel_for\n");
    return 0;
}

// Test 4: parallel_invoke
static int test_parallel_invoke() {
    std::atomic<int> counter{0};
    async::parallel_invoke(
        [&] { counter.fetch_add(1, std::memory_order_relaxed); },
        [&] { counter.fetch_add(2, std::memory_order_relaxed); },
        [&] { counter.fetch_add(3, std::memory_order_relaxed); }
    );
    if (counter.load() != 6) {
        std::fprintf(stderr, "FAIL: parallel_invoke counter = %d, expected 6\n",
                     counter.load());
        return 1;
    }
    std::printf("  PASS: parallel_invoke\n");
    return 0;
}

int main() {
    std::printf("asyncplusplus 1.2 test_package:\n");
    int failures = 0;
    failures += test_task_spawn();
    failures += test_continuation();
    failures += test_parallel_for();
    failures += test_parallel_invoke();
    if (failures == 0) {
        std::printf("All 4 tests passed.\n");
        return 0;
    }
    std::fprintf(stderr, "%d test(s) FAILED.\n", failures);
    return 1;
}
