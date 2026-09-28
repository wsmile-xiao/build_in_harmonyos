// HarmonyOS-specific test for ctrack.
// Verifies that the public tracking API remains correct and thread-safe on
// the OHOS platform: per-thread event isolation, thread-count reporting,
// and aggregated summary integrity under real multi-threaded execution.
// Uses ONLY the public header ctrack.hpp and its public API.
#include <atomic>
#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <vector>
#include "ctrack.hpp"

static const int kThreads = 4;
static const int kIterations = 200;

static void worker(int worker_id) {
    CTRACK_NAME("ohos_worker");
    volatile double acc = 0.0;
    for (int i = 0; i < kIterations; ++i) {
        acc += static_cast<double>(i) * 0.5;
    }
    (void)acc;
    (void)worker_id;
}

int main() {
    // 1) Basic single-thread tracking works on OHOS.
    // Note: events are flushed into the store when the EventHandler goes out
    // of scope, so result_get_tables() must be called after the scope ends.
    {
        CTRACK_NAME("ohos_single");
        volatile int s = 0;
        for (int i = 0; i < 100; ++i) s += i;
        (void)s;
    }
    {
        auto tables = ctrack::result_get_tables();
        bool found = false;
        for (const auto &row : tables.summary.rows) {
            if (row.function_name.find("ohos_single") != std::string::npos &&
                row.calls == 1) {
                found = true;
            }
        }
        if (!found) {
            std::cerr << "FAIL: single-thread tracking entry missing" << std::endl;
            return 1;
        }
    }

    // 2) Multi-threaded tracking: per-thread events must be recorded and
    //    the function must be reported with the correct total call count.
    {
        std::vector<std::thread> pool;
        for (int t = 0; t < kThreads; ++t) {
            pool.emplace_back(worker, t);
        }
        for (auto &th : pool) {
            th.join();
        }

        auto tables = ctrack::result_get_tables();
        int calls = 0;
        int threads = 0;
        for (const auto &d : tables.details.rows) {
            if (d.function_name.find("ohos_worker") != std::string::npos) {
                calls = d.calls;
                threads = d.threads;
            }
        }
        if (calls != kThreads) {
            std::cerr << "FAIL: ohos_worker calls=" << calls
                      << ", expected " << kThreads << std::endl;
            return 1;
        }
        if (threads != kThreads) {
            std::cerr << "FAIL: ohos_worker threads=" << threads
                      << ", expected " << kThreads << std::endl;
            return 1;
        }
        if (tables.details.rows.empty()) {
            std::cerr << "FAIL: detail table empty" << std::endl;
            return 1;
        }
    }

    // 3) Summary/detail table integrity: non-negative times and percentages.
    //    R02 修复：events 在 EventHandler 离开作用域时才写入 store，
    //    因此 result_get_tables() 必须在 CTRACK_NAME 作用域结束之后调用，
    //    否则 ohos_integrity 条目尚未落库，完整性断言整体空转。
    {
        CTRACK_NAME("ohos_integrity");
        volatile int s = 0;
        for (int i = 0; i < 50; ++i) s += i * 2;
        (void)s;
    }
    {
        auto tables = ctrack::result_get_tables();
        int integrity_rows = 0;
        for (const auto &d : tables.details.rows) {
            if (d.function_name.find("ohos_integrity") != std::string::npos) {
                ++integrity_rows;
            }
            if (d.time_acc.count() < 0 || d.time_ae_all.count() < 0 ||
                d.time_a_all.count() < 0) {
                std::cerr << "FAIL: negative timing in detail row: "
                          << d.function_name << std::endl;
                return 1;
            }
            if (d.calls < 1 || d.threads < 1) {
                std::cerr << "FAIL: invalid calls/threads in detail row" << std::endl;
                return 1;
            }
        }
        if (integrity_rows != 1) {
            std::cerr << "FAIL: ohos_integrity entry missing from detail table "
                      << "(integrity_rows=" << integrity_rows << ")" << std::endl;
            return 1;
        }
    }

    std::cout << "ctrack OHOS special test PASSED: single-thread tracking, "
              << kThreads << "-thread isolation (threads=" << kThreads
              << ", calls=" << kThreads << "), table integrity OK" << std::endl;
    return 0;
}