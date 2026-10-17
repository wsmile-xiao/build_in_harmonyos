#include <paryfor.hpp>

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <functional>
#include <numeric>
#include <vector>

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
    constexpr std::uint64_t count = 2048;
    std::vector<std::atomic<unsigned>> visits(count);
    std::atomic<std::uint64_t> total{0};
    std::atomic<bool> thread_ids_valid{true};

    paryfor::parallel_for<std::uint64_t>(
        0, count, 4,
        std::function<void(std::uint64_t, int)>(
            [&](std::uint64_t i, int thread_id) {
                visits[i].fetch_add(1, std::memory_order_relaxed);
                total.fetch_add(i, std::memory_order_relaxed);
                if (thread_id < 0 || thread_id >= 4) {
                    thread_ids_valid.store(false, std::memory_order_relaxed);
                }
            }));

    bool exactly_once = true;
    for (const auto& visit : visits) {
        exactly_once = exactly_once
            && visit.load(std::memory_order_relaxed) == 1;
    }
    const std::uint64_t expected = count * (count - 1) / 2;
    check(exactly_once, "unchunked overload visits every index exactly once");
    check(total.load() == expected, "unchunked overload preserves arithmetic sum");
    check(thread_ids_valid.load(), "thread-id overload returns valid worker ids");

    std::atomic<std::uint64_t> no_id_sum{0};
    paryfor::parallel_for<std::uint64_t>(
        0, count, 3,
        std::function<void(std::uint64_t)>(
            [&](std::uint64_t i) {
                no_id_sum.fetch_add(i, std::memory_order_relaxed);
            }));
    check(no_id_sum.load() == expected, "callback-without-id overload completes all work");

    std::vector<std::atomic<unsigned>> chunk_visits(count);
    std::atomic<std::uint64_t> chunk_sum{0};
    paryfor::parallel_for<std::uint64_t>(
        0, count, 4, 31,
        std::function<void(std::uint64_t, int)>(
            [&](std::uint64_t i, int) {
                chunk_visits[i].fetch_add(1, std::memory_order_relaxed);
                chunk_sum.fetch_add(i, std::memory_order_relaxed);
            }));
    bool chunks_exactly_once = true;
    for (const auto& visit : chunk_visits) {
        chunks_exactly_once = chunks_exactly_once
            && visit.load(std::memory_order_relaxed) == 1;
    }
    check(chunks_exactly_once, "chunked overload visits every index exactly once");
    check(chunk_sum.load() == expected, "chunked overload preserves arithmetic sum");

    paryfor::atomic_queue::AtomicQueue2<std::uint64_t, 64> queue;
    check(queue.capacity() == 64, "public atomic queue reports configured capacity");
    check(queue.try_push(17) && queue.pop() == 17,
          "public atomic queue push/pop round-trip succeeds");

    std::printf("test_paryfor: %s (8 checks)\n",
                failures == 0 ? "ALL PASS" : "FAILED");
    return failures == 0 ? 0 : 1;
}
