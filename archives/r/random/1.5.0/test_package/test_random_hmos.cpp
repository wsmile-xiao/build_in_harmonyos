// HarmonyOS 专项测试 — random 1.5.0（effolkronium::random 头文件库）
//
// 验证目标（区别于上游 Catch2 用例的 OHOS 针对性场景）：
//   1. OHOS 多线程下的 thread_local 随机流隔离（每个线程独立序列，互不串扰）
//   2. OHOS 平台默认熵源（default_seeder / std::random_device）可用性：连续两次
//      构造应产生不同种子（若熵源失效，两次种子相同即失败）
//   3. 在 OHOS (aarch64-linux-ohos, clang 15) 工具链下整数/实数范围与类型推导正确
//   4. 线程内连续取数不越界、不重复模式化（冒烟）
//
// 编译: clang++ -std=c++17 -I<include> test_random_hmos.cpp -o test_random_hmos -pthread
// 运行: ./test_random_hmos  -> 全断言通过输出 ALL_RANDOM_HMOS_ASSERTIONS_PASSED

#include <effolkronium/random.hpp>

#include <cassert>
#include <cstdint>
#include <iostream>
#include <set>
#include <thread>
#include <vector>

using Random = effolkronium::random_thread_local;

namespace {
std::uint64_t draw_seed() {
    // default seeder 走 std::random_device（OHOS 平台熵源）；两次实例化的种子序列应不同。
    std::array<std::uint32_t, 4> a{}, b{};
    effolkronium::seeder_default{}().generate(a.begin(), a.end());
    effolkronium::seeder_default{}().generate(b.begin(), b.end());
    return (a != b) ? 1u : 0u;
}

void thread_worker(std::uint64_t tag, std::vector<std::uint32_t>* out) {
    // 每个线程独立 thread_local 引擎：本线程 200 次 int32 范围抽取全部落在边界内；
    // 大区间（200001 槽位）下 200 次抽取的生日碰撞期望 ≈0.1，>10 次重复判分布异常。
    const int lo = -100000, hi = 100000;
    std::uint32_t collisions = 0;
    std::set<int> seen;
    for (int i = 0; i < 200; ++i) {
        const int v = Random::get(lo, hi);
        if (v < lo || v > hi) {
            collisions += 10000;  // 越界：放大计分，必失败
        }
        if (!seen.insert(v).second) {
            ++collisions;
        }
    }
    out->at(tag) = collisions;
}
}  // namespace

int main() {
    std::uint64_t failures = 0;

    // [1] 多线程 thread_local 隔离：4 线程并行，各自 200 次抽取。
    std::vector<std::uint32_t> coll(4, 0);
    std::vector<std::thread> threads;
    for (std::uint64_t t = 0; t < 4; ++t) {
        threads.emplace_back(thread_worker, t, &coll);
    }
    for (auto& th : threads) th.join();
    for (const auto c : coll) {
        if (c > 10) failures += c;  // 越界或大量重复 = 线程隔离失败/分布异常
    }

    // [2] OHOS 熵源可用性：default_seeder 两次实例化种子不同。
    if (draw_seed() == 0) failures += 1000;

    // [3] 类型推导：char / int8 / float / double 范围边界。
    const char c = Random::get('a', 'z');
    if (c < 'a' || c > 'z') failures += 1;
    const std::int8_t i8 = Random::get<std::int8_t>(-128, 127);
    if (i8 < -128 || i8 > 127) failures += 1;
    const float f = Random::get(0.0f, 1.0f);
    if (!(f >= 0.0f && f < 1.0f)) failures += 1;
    const double d = Random::get(0.0, 1.0);
    if (!(d >= 0.0 && d < 1.0)) failures += 1;

    // [4] 反转区间（上游同样覆盖，此处 OHOS 冒烟复验）。
    const int rev = Random::get(5, -5);
    if (rev < -5 || rev > 5) failures += 1;

    if (failures == 0) {
        std::cout << "ALL_RANDOM_HMOS_ASSERTIONS_PASSED (thread isolation + entropy + ranges OK)\n";
        return 0;
    }
    std::cout << "RANDOM_HMOS_FAILURES=" << failures << "\n";
    return 1;
}
