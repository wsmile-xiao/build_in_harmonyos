#include <rapidfuzz/fuzz.hpp>
#include <rapidfuzz/distance.hpp>
#include <cstdio>
#include <cstddef>
#include <cstdlib>

// test_package 消费者验证 (R34): 必须实质调用被测包 API
// 覆盖 fuzz::ratio / fuzz::partial_ratio / token_set_ratio 与 distance 算法
int main()
{
    const double ratio = rapidfuzz::fuzz::ratio("this is a test", "this is a test!");
    if (ratio < 95.0) {
        std::printf("FAIL: fuzz::ratio expected >= 95, got %.2f\n", ratio);
        return EXIT_FAILURE;
    }

    const double partial = rapidfuzz::fuzz::partial_ratio("this is a test", "this is a test!");
    if (partial < 99.0) {
        std::printf("FAIL: fuzz::partial_ratio expected >= 99, got %.2f\n", partial);
        return EXIT_FAILURE;
    }

    const double token_set = rapidfuzz::fuzz::token_set_ratio(
        "fuzzy was a bear", "fuzzy fuzzy was a bear");
    if (token_set < 90.0) {
        std::printf("FAIL: fuzz::token_set_ratio expected >= 90, got %.2f\n", token_set);
        return EXIT_FAILURE;
    }

    const std::size_t lev = rapidfuzz::levenshtein_distance(
        "lewenstein", "levenshtein");
    if (lev != 2) {
        std::printf("FAIL: levenshtein_distance expected 2, got %zu\n", lev);
        return EXIT_FAILURE;
    }

    const std::size_t hamming = rapidfuzz::hamming_distance("abcde", "abcde");
    if (hamming != 0) {
        std::printf("FAIL: hamming_distance(expected same) expected 0, got %zu\n", hamming);
        return EXIT_FAILURE;
    }

    std::printf("OK: rapidfuzz-cpp consumer test passed "
                "(ratio=%.2f partial=%.2f token_set=%.2f lev=%zu hamming=%zu)\n",
                ratio, partial, token_set, lev, hamming);
    return EXIT_SUCCESS;
}