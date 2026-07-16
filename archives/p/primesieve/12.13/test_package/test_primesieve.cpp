// test_primesieve.cpp — primesieve 12.13 smoke test
// 验证质数生成、计数、第 N 个质数功能

#include <primesieve.hpp>
#include <cstdio>
#include <vector>

int main() {
    int errors = 0;

    // 测试 1: 使用 iterator 生成前 10 个质数
    primesieve::iterator it;
    uint64_t expected_primes[] = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29};
    for (int i = 0; i < 10; i++) {
        uint64_t p = it.next_prime();
        if (p != expected_primes[i]) {
            printf("FAIL: 第 %d 个质数期望 %llu, 实际 %llu\n", i + 1, (unsigned long long)expected_primes[i], (unsigned long long)p);
            errors++;
        }
    }
    printf("测试 1 (iterator 生成前 10 个质数): %s\n", errors == 0 ? "通过" : "失败");

    // 测试 2: count_primes — 统计 0-10 范围内的质数
    uint64_t count = primesieve::count_primes(0, 10);
    if (count != 4) {
        printf("FAIL: 0-10 范围质数计数期望 4, 实际 %llu\n", (unsigned long long)count);
        errors++;
    }
    printf("测试 2 (count_primes 0-10 = %llu): %s\n", (unsigned long long)count, count == 4 ? "通过" : "失败");

    // 测试 3: nth_prime — 第 100 个质数是 541
    uint64_t p100 = primesieve::nth_prime(100);
    if (p100 != 541) {
        printf("FAIL: 第 100 个质数期望 541, 实际 %llu\n", (unsigned long long)p100);
        errors++;
    }
    printf("测试 3 (nth_prime(100) = %llu): %s\n", (unsigned long long)p100, p100 == 541 ? "通过" : "失败");

    // 测试 4: generate_primes — 生成 0-30 范围内的质数
    std::vector<uint64_t> primes;
    primesieve::generate_primes(0, 30, &primes);
    // 0-30 范围内有 10 个质数: 2,3,5,7,11,13,17,19,23,29
    if (primes.size() != 10) {
        printf("FAIL: 0-30 范围质数数量期望 10, 实际 %zu\n", primes.size());
        errors++;
    }
    printf("测试 4 (generate_primes 0-30, 数量=%zu): %s\n", primes.size(), primes.size() == 10 ? "通过" : "失败");

    // 汇总
    printf("\n========================================\n");
    printf("测试结果: %d 个错误\n", errors);
    printf("========================================\n");

    if (errors > 0) {
        printf("FAIL: 存在 %d 个测试失败\n", errors);
        return 1;
    }

    printf("ALL TESTS PASSED\n");
    return 0;
}
