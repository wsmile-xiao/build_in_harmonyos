// ohos_special_test.cpp — hpptools 1.1.3 HarmonyOS 专项测试
//
// 本用例为鸿蒙专项测试（区别于上游 examples 与 test_package 消费者用例）：
// 在 OHOS 平台（aarch64-unknown-linux-ohos）实际运行 hpptools 的线程类
// 组件（pfor 并行循环 / tpool 线程池）与 logger 设施，验证：
//   1) pthread 运行时在 OHOS 上可用，pfor/tpool 真实创建并运行多线程；
//   2) tpool 工作线程可观测地消费任务（完成计数）；
//   3) logger 设施级日志按级别过滤正确输出。
// 不包含上游测试代码，是独立编写的平台专项用例。
#include <atomic>
#include <cassert>
#include <iostream>
#include <vector>

#include "pfor.hpp"
#include "tpool.hpp"
#include "logger.hpp"

int main() {
    // 1) pfor: 4 线程并行填充 1..N 平方
    const unsigned N = 1000;
    std::vector<unsigned> v(N);
    unsigned crt = 0;
    pfor::pfor<unsigned>(
        4,                     // num_threads
        100,                   // chunk_size
        [&](unsigned& i) {     // get_item
            if (crt >= N) return false;
            i = crt++; return true;
        },
        [&](unsigned& i) {     // process_item
            v[i] = i * i;
        });
    for (unsigned i = 0; i < N; ++i) {
        if (v[i] != i * i) {
            std::cerr << "FAIL: pfor v[" << i << "]=" << v[i] << "\n";
            return 1;
        }
    }
    std::cout << "pfor OK: " << N << " items squared by 4 threads\n";

    // 2) tpool: 提交 32 个自增作业，等待全部完成
    tpool::tpool pool(4);
    std::atomic<int> counter{0};
    for (int i = 0; i < 32; ++i) {
        pool.add_job([&](unsigned) { counter.fetch_add(1); });
    }
    pool.wait_jobs();
    if (counter.load() != 32) {
        std::cerr << "FAIL: tpool counter=" << counter.load() << "\n";
        return 1;
    }
    std::cout << "tpool OK: 32 jobs completed by 4 workers\n";

    // 3) logger: 默认 info 级别 → debug 被抑制、info 输出
    logger::Logger::set_default_level("info");
    int debug_calls = 0, info_calls = 0;
    LOG(debug) << "suppressed debug msg; calls=" << ++debug_calls;
    LOG(info) << "visible info msg; calls=" << ++info_calls;
    if (debug_calls != 0) {
        std::cerr << "FAIL: debug log should be suppressed at info level\n";
        return 1;
    }
    if (info_calls != 1) {
        std::cerr << "FAIL: info log should be emitted once\n";
        return 1;
    }
    std::cout << "logger OK: debug suppressed, info emitted\n";

    std::cout << "ohos_special_test: ALL PASSED\n";
    return 0;
}
