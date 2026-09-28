#include <paryfor.hpp>

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <functional>
#include <vector>

#ifndef __OHOS__
#error "test_paryfor_ohos.cpp must be compiled by the HarmonyOS toolchain"
#endif

#ifndef __aarch64__
#error "test_paryfor_ohos.cpp validates the HarmonyOS PC AArch64 code path"
#endif

namespace {
int failures = 0;

void check(bool condition, const char* label) {
    if (condition) {
        std::printf("[ok] %s\n", label);
    } else {
        std::printf("[FAIL] %s\n", label);
        ++failures;
    }
}
}  // namespace

int main() {
    paryfor::atomic_queue::AtomicQueue2<std::uint64_t, 64> queue;
    check(queue.capacity() == 64, "OHOS AArch64 queue capacity is stable");

    bool pushed = true;
    for (std::uint64_t value = 1; value <= 32; ++value) {
        pushed = pushed && queue.try_push(value);
    }
    check(pushed, "OHOS AArch64 atomic queue accepts a burst");

    bool fifo = true;
    for (std::uint64_t expected = 1; expected <= 32; ++expected) {
        std::uint64_t actual = 0;
        fifo = fifo && queue.try_pop(actual) && actual == expected;
    }
    check(fifo, "OHOS AArch64 atomic queue preserves single-producer order");
    check(queue.was_empty(), "OHOS AArch64 atomic queue drains completely");

    constexpr std::uint64_t iterations = 8192;
    std::vector<std::atomic<unsigned>> visits(iterations);
    std::atomic<std::uint64_t> completed{0};
    paryfor::parallel_for<std::uint64_t>(
        0, iterations, 8, 37,
        std::function<void(std::uint64_t, int)>(
            [&](std::uint64_t i, int) {
                visits[i].fetch_add(1, std::memory_order_relaxed);
                completed.fetch_add(1, std::memory_order_relaxed);
            }));

    bool exactly_once = true;
    for (const auto& visit : visits) {
        exactly_once = exactly_once
            && visit.load(std::memory_order_relaxed) == 1;
    }
    check(completed.load() == iterations,
          "OHOS parallel_for completes the full AArch64 stress range");
    check(exactly_once,
          "OHOS parallel_for processes each AArch64 stress index exactly once");

    std::printf("test_paryfor_ohos: %s (6 checks)\n",
                failures == 0 ? "ALL PASS" : "FAILED");
    return failures == 0 ? 0 : 1;
}
