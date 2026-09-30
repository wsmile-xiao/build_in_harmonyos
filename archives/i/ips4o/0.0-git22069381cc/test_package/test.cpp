// test_package consumer test — 通过已安装/导出的公开头文件 <ips4o.hpp>
// 调用 ips4o::sort 公开 API，并验证排序结果与参考实现 std::sort 一致。
#include <ips4o.hpp>
#include <vector>
#include <cstdint>
#include <cstdio>
#include <algorithm>

int main() {
    constexpr size_t N = 1u << 20;
    std::vector<uint64_t> input(N), a(N), b(N);
    for (size_t i = 0; i < N; ++i) {
        input[i] = static_cast<uint64_t>(i * 2654435761u + 7u);
    }
    a = input;
    b = input;
    // 被测公开 API：ips4o::sort（顺序排序）
    ips4o::sort(a.begin(), a.end());
    // 参考实现
    std::sort(b.begin(), b.end());
    const bool equal = std::equal(a.begin(), a.end(), b.begin());
    std::printf("ips4o::sort result matches std::sort: %s\n", equal ? "PASS" : "FAIL");
    return equal ? 0 : 1;
}