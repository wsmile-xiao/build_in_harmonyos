// HarmonyOS 专项测试：cpp-sort 2.2.0 真实消费入口验证
// 使用 OHOS armv8 工具链（clang 15 / aarch64-linux-ohos）实际编译并运行，
// 验证 header-only 库在 OHOS 平台下的可编译性与运行时正确性。
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstddef>
#include <random>
#include <vector>

#include <cpp-sort/adapters.h>
#include <cpp-sort/fixed_sorters.h>
#include <cpp-sort/sorters.h>
#include <cpp-sort/utility/functional.h>

int main() {
    int failures = 0;
    const std::size_t N = 4096;
    std::mt19937 rng(20260902);

    // 1) 大规模随机数据 + 通用 hybrid_adapter 排序（覆盖 pdq_sorter/merge_sorter 分派）
    std::vector<int> data(N);
    for (auto& v : data) v = static_cast<int>(rng() % 100000);
    cppsort::hybrid_adapter<cppsort::pdq_sorter, cppsort::merge_sorter> sorter;
    sorter(data);
    if (!std::is_sorted(data.begin(), data.end())) {
        std::printf("FAIL: hybrid_adapter sort not sorted\n");
        failures++;
    }

    // 2) 稳定排序验证：pair（key,ord）按 key 排序后同名元素保持原序
    std::vector<std::pair<int, int>> kv;
    for (std::size_t i = 0; i < N; ++i) kv.push_back({static_cast<int>(rng() % 100), static_cast<int>(i)});
    cppsort::merge_sort(kv, [](const auto& lhs, const auto& rhs) { return lhs.first < rhs.first; });
    bool stable = true;
    for (std::size_t i = 1; i < kv.size(); ++i) {
        if (kv[i - 1].first == kv[i].first && kv[i - 1].second > kv[i].second) { stable = false; break; }
    }
    if (!stable) { std::printf("FAIL: merge_sort not stable\n"); failures++; }

    // 3) 8 元素以内固定排序网络（fixed sorting_network_sorter<8>）
    std::array<int, 8> arr = {7, 3, 5, 1, 6, 2, 4, 0};
    cppsort::sorting_network_sorter<8>{}(arr);
    if (!std::is_sorted(arr.begin(), arr.end())) {
        std::printf("FAIL: sorting_network_sorter<8> not sorted\n");
        failures++;
    }

    if (failures == 0) {
        std::printf("cpp-sort 2.2.0 OHOS special test: PASSED (%zu elements, 3 scenarios)\n", N);
        return 0;
    }
    std::printf("cpp-sort 2.2.0 OHOS special test: FAILED (%d)\n", failures);
    return 1;
}