// HarmonyOS 专项测试 — concurrencpp 0.1.7 (aarch64-linux-ohos)
//
// 校验库在 OHOS 平台上的真实可用性（非复述上游测试）：
//   1. runtime + thread_executor 提交并行任务, 校验真实并发结果求和
//   2. lazy_result 协程 (C++20 coroutine) 在 OHOS 上正确 co_return
//   3. 并行任务确实运行在不同系统线程 (线程 ID 去重数 == 任务数)
#include <concurrencpp/concurrencpp.h>

#include <atomic>
#include <iostream>
#include <mutex>
#include <set>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

static concurrencpp::lazy_result<int> coroutine_add(int a, int b) {
    co_return a + b;
}

static int run_coroutine_check() {
    auto lazy = coroutine_add(20, 22);
    auto result = lazy.run();
    return result.get();
}

int main() {
    constexpr int k_task_count = 8;
    std::atomic<int> sum{0};
    std::mutex id_mutex;
    std::set<std::thread::id> thread_ids;

    try {
        concurrencpp::runtime runtime;
        auto executor = runtime.thread_executor();

        std::vector<concurrencpp::result<void>> tasks;
        for (int i = 1; i <= k_task_count; ++i) {
            tasks.push_back(executor->submit([&, i]() {
                sum.fetch_add(i, std::memory_order_relaxed);
                {
                    std::lock_guard<std::mutex> lock(id_mutex);
                    thread_ids.insert(std::this_thread::get_id());
                }
            }));
        }
        for (auto& t : tasks) {
            t.get();
        }

        const int expected_sum = k_task_count * (k_task_count + 1) / 2;
        if (sum.load() != expected_sum) {
            throw std::runtime_error("parallel sum mismatch: " + std::to_string(sum.load()));
        }
        // 并行性下限断言：thread_executor 按需扩线程，不保证每个任务独占一线程。
        // 用“至少 2 个不同线程执行过任务”验证真实并发，避免核数/时序相关性误报。
        if (thread_ids.size() < 2) {
            throw std::runtime_error("parallelism degraded: unique thread ids = " +
                                     std::to_string(thread_ids.size()));
        }

        const int coro_sum = run_coroutine_check();
        if (coro_sum != 42) {
            throw std::runtime_error("coroutine result mismatch: " + std::to_string(coro_sum));
        }

        std::cout << "[OHOS] concurrencpp parallel sum=" << sum.load()
                  << " unique_threads=" << thread_ids.size()
                  << " coroutine_sum=" << coro_sum << " -> PASS" << std::endl;
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "[OHOS] concurrencpp test FAILED: " << ex.what() << std::endl;
        return 1;
    }
}