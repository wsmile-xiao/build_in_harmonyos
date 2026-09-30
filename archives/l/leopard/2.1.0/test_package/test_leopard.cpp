// Consumer probe for leopard 2.1.0 (hmthrp::ThreadPool / hmthrp::SharedQueue).
//
// Every check below exercises the packaged headers through the public API that
// a downstream consumer would use: dispatch(), parallel_loop(), parallel_sort()
// and the SharedQueue FIFO.  10 explicit checks, all must pass.
#include <Leopard/SharedQueue.h>
#include <Leopard/ThreadPool.h>

#include <algorithm>
#include <cstddef>
#include <future>
#include <iostream>
#include <numeric>
#include <vector>

namespace {

int g_checks = 0;
int g_failures = 0;

void check(bool ok, const char *what)
{
    ++g_checks;
    if (ok) {
        std::cout << "PASS: " << what << std::endl;
    }
    else {
        ++g_failures;
        std::cout << "FAIL: " << what << std::endl;
    }
}

}  // namespace

int main()
{
    using hmthrp::SharedQueue;
    using hmthrp::ThreadPool;

    ThreadPool pool(4);

    check(pool.capacity_threads() == 4, "capacity_threads reflects the requested pool size");

    auto one = pool.dispatch(false,
                             [](std::size_t i) -> std::size_t { return i * i; },
                             std::size_t(10));
    check(one.get() == 100, "dispatch() returns the callable result through std::future");

    constexpr std::size_t batch = 64;
    std::vector<std::future<std::size_t>> futs;
    futs.reserve(batch);
    for (std::size_t i = 0; i < batch; ++i)
        futs.push_back(pool.dispatch(false,
                                     [](std::size_t i) -> std::size_t { return i * 2; },
                                     i));

    bool        per_task = true;
    std::size_t total = 0;
    for (std::size_t i = 0; i < batch; ++i) {
        const std::size_t value = futs[i].get();
        if (value != i * 2)
            per_task = false;
        total += value;
    }
    check(per_task, "64 dispatched tasks each return their own result");
    check(total == batch * (batch - 1), "batch results aggregate to the expected sum");

    const std::size_t            n = 10003;
    std::vector<std::size_t>     vec(n);
    std::iota(vec.begin(), vec.end(), 1);
    auto sum_range = [](const auto &begin, const auto &end) -> std::size_t {
        std::size_t sum = 0;
        for (auto iter = begin; iter != end; ++iter)
            sum += *iter;
        return sum;
    };
    auto loop_futs = pool.parallel_loop(vec.cbegin(), vec.cend(), sum_range);
    std::size_t loop_sum = 0;
    for (auto &fut : loop_futs)
        loop_sum += fut.get();
    check(!loop_futs.empty(), "parallel_loop() dispatches at least one block");
    check(loop_sum == n * (n + 1) / 2, "parallel_loop() covers the whole input range");

    std::vector<int> data(4096);
    for (std::size_t i = 0; i < data.size(); ++i)
        data[i] = static_cast<int>((i * 7919) % 4096);
    pool.parallel_sort(data.begin(), data.end());
    check(std::is_sorted(data.begin(), data.end()),
          "parallel_sort() produces a non-decreasing sequence");

    SharedQueue<int> queue;
    for (int i = 0; i < 8; ++i)
        queue.push(i);
    bool fifo = true;
    for (int i = 0; i < 8; ++i) {
        if (queue.front() != i)
            fifo = false;
        (void)queue.pop_front();
    }
    check(fifo, "SharedQueue<> preserves FIFO order over 8 elements");
    check(queue.empty() && queue.size() == 0, "SharedQueue<> reports empty after draining");

    pool.shutdown();
    check(pool.is_shutdown(), "shutdown() flips is_shutdown() to true");

    std::cout << "CHECKS=" << g_checks << " FAILURES=" << g_failures << std::endl;
    return g_failures == 0 ? 0 : 1;
}
