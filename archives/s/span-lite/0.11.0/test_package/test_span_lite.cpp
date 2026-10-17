// test_span_lite.cpp — span-lite 0.11.0 HarmonyOS 专项测试用例（真实可执行）
// 覆盖 nonstd::span 的核心消费入口：构造/索引/size/迭代器/子视图
#include <nonstd/span.hpp>
#include <cstdio>
#include <vector>

int main()
{
    int arr[5] = {10, 20, 30, 40, 50};

    // 数组构造 + size + 元素访问
    nonstd::span<int> s(arr);
    if (s.size() != 5) { std::printf("FAIL: size\n"); return 1; }
    if (s[0] != 10 || s[4] != 50) { std::printf("FAIL: element access\n"); return 2; }

    // first/last 子视图
    auto head = s.first(2);
    auto tail = s.last(2);
    if (head.size() != 2 || tail[1] != 50) { std::printf("FAIL: first/last\n"); return 3; }

    // subspan
    auto mid = s.subspan(1, 3);
    if (mid.size() != 3 || mid[0] != 20) { std::printf("FAIL: subspan\n"); return 4; }

    // 迭代器遍历求和
    int sum = 0;
    for (auto v : s) { sum += v; }
    if (sum != 150) { std::printf("FAIL: iterate sum\n"); return 5; }

    // 从 std::vector 构造
    std::vector<int> v = {1, 2, 3};
    nonstd::span<const int> vs(v);
    if (vs.size() != 3 || vs[2] != 3) { std::printf("FAIL: vector span\n"); return 6; }

    std::printf("PASS: span-lite header-only 库链接和核心 API 验证通过 (size=%zu, sum=%d)\n", (size_t)s.size(), sum);
    return 0;
}
