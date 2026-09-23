#include <cstdio>
#include <cstring>
#include <darts.h>

/* 鸿蒙特有消费者测试（R34 反空壳）：真实使用 Darts::DoubleArray 建典+检索。 */
int main() {
    const char *keys[] = {"abc", "abd", "ac"};
    std::size_t lengths[] = {3, 3, 2};
    int values[] = {10, 20, 30};

    Darts::DoubleArray da;
    if (da.build(3, keys, lengths, values) != 0) {
        std::printf("FAIL build\n");
        return 1;
    }
    for (int i = 0; i < 3; ++i) {
        Darts::DoubleArray::result_pair_type r =
            da.exactMatchSearch<Darts::DoubleArray::result_pair_type>(keys[i]);
        if (r.value != values[i] || r.length != lengths[i]) {
            std::printf("FAIL exactMatch %s -> %d/%u\n", keys[i], r.value, (unsigned)r.length);
            return 1;
        }
    }
    /* 不存在键必须 miss */
    if (da.exactMatchSearch<Darts::DoubleArray::result_pair_type>("abx").value != -1) {
        std::printf("FAIL miss detection\n");
        return 1;
    }
    /* commonPrefixSearch("abcd") 应命中 abc(10) 与 abd? 否——abcd 的前缀键只有 abc */
    Darts::DoubleArray::result_pair_type results[8];
    std::size_t n = da.commonPrefixSearch("abcd", results, 8);
    if (n != 1 || results[0].value != 10) {
        std::printf("FAIL prefixSearch n=%u\n", (unsigned)n);
        return 1;
    }
    std::printf("PASS test_darts (build/exact/miss/prefix ok)\n");
    return 0;
}
