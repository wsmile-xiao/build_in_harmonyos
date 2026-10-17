#include <atomic>
#include <cassert>
#include <iostream>
#include <numeric>
#include <vector>
#include "BS_thread_pool.hpp"

int main()
{
    int total = 0;
    int passed = 0;
    auto check = [&](bool cond, const char* name) {
        ++total;
        if (cond) {
            ++passed;
            std::cout << "check " << total << " (" << name << ") -> passed." << std::endl;
        } else {
            std::cout << "check " << total << " (" << name << ") -> FAILED!" << std::endl;
        }
    };
    // 1: thread count matches construction argument.
    BS::thread_pool pool(4);
    check(pool.get_thread_count() == 4, "thread_count");
    // 2: submit_task returns correct future value.
    auto fut = pool.submit_task([] { return 40 + 2; });
    check(fut.get() == 42, "submit_task");
    // 3: detach_task executes (atomic counter).
    std::atomic<int> counter{0};
    pool.detach_task([&counter] { counter.fetch_add(1); });
    pool.wait();
    check(counter.load() == 1, "detach_task");
    // 4: detach_loop parallel sum (loop func takes a single index).
    std::vector<int> vals(100);
    std::iota(vals.begin(), vals.end(), 1);
    std::atomic<long> sum{0};
    pool.detach_loop(0, vals.size(), [&](std::size_t i) {
        sum.fetch_add(vals[i]);
    });
    pool.wait();
    check(sum.load() == 5050, "detach_loop");
    // 5: submit_blocks returns futures covering the whole range.
    auto futures = pool.submit_blocks(0, 100, [](std::size_t a, std::size_t b) {
        int s = 0;
        for (std::size_t i = a; i < b; ++i)
            s += static_cast<int>(i);
        return s;
    });
    int block_sum = 0;
    for (auto& f : futures)
        block_sum += f.get();
    check(block_sum == 4950, "submit_blocks");
    // 6: submit_sequence produces one future per index.
    auto seq = pool.submit_sequence(0, 10, [](std::size_t i) { return static_cast<int>(i * 2); });
    int seq_sum = 0;
    for (auto& f : seq)
        seq_sum += f.get();
    check(seq_sum == 90, "submit_sequence");
    std::cout << "PASS: " << passed << "/" << total << " checks passed." << std::endl;
    if (passed == total) {
        std::cout << "HMBS_TEST_DETAIL total=" << total << " passed=" << passed << std::endl;
        return 0;
    }
    return 1;
}
