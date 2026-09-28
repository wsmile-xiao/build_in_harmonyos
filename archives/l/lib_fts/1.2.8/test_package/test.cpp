// test.cpp — lib_fts 消费者用例（test_package L1）
// 仅通过已安装公开头文件 <fts_fuzzy_match.h> 调用公开 API：
//   fts::fuzzy_match_simple(pattern, str) -> bool
//   fts::fuzzy_match(pattern, str, int& score) -> bool
// STB 风格单头文件库：使用方在 include 前定义 FTS_FUZZY_MATCH_IMPLEMENTATION
// 以在本翻译单元实例化实现（上游 tests 同此用法）。
#define FTS_FUZZY_MATCH_IMPLEMENTATION
#include <fts_fuzzy_match.h>

#include <cstdio>
#include <cstdlib>

static int failures = 0;

static void check(bool cond, const char *name) {
    if (cond) {
        std::printf("PASS %s\n", name);
    } else {
        std::printf("FAIL %s\n", name);
        ++failures;
    }
}

int main() {
    // 文档示例（docs/fuzzy_match.md）：简单匹配（fuzzy_match_simple 是公开 API）
    check(fts::fuzzy_match_simple("ftw", "ForrestTheWoods"), "simple: ftw in ForrestTheWoods");
    check(!fts::fuzzy_match_simple("fwt", "ForrestTheWoods"), "simple: fwt NOT in ForrestTheWoods");
    check(fts::fuzzy_match_simple("gh", "GitHub"), "simple: gh in GitHub");
    check(fts::fuzzy_match_simple("", "anything"), "simple: empty pattern matches");

    // 打分匹配：文档示例分值语义（score 越高越好；可匹配返回 true）
    int score = 0;
    check(fts::fuzzy_match("otw", "Power of the Wild", score), "scored: otw in Power of the Wild");
    std::printf("score[otw/Power of the Wild] = %d\n", score);
    check(score > 0, "scored: positive score for good match");

    score = 0;
    check(fts::fuzzy_match("abc", "xyz", score) == false, "scored: abc NOT in xyz");
    check(score == 0, "scored: no match leaves score untouched");

    // 大小写不敏感
    check(fts::fuzzy_match_simple("GITHUB", "github"), "case-insensitive: GITHUB in github");
    check(fts::fuzzy_match_simple("github", "GiThUb"), "case-insensitive: github in GiThUb");

    // fuzzy_match_simple 也在公开头中
    check(fts::fuzzy_match_simple("fts", "lib_fts") == true, "simple-api: fts in lib_fts");
    check(fts::fuzzy_match_simple("xyz", "lib_fts") == false, "simple-api: xyz NOT in lib_fts");

    if (failures == 0) {
        std::printf("ALL TESTS PASSED\n");
        return 0;
    }
    std::printf("%d TEST(S) FAILED\n", failures);
    return 1;
}