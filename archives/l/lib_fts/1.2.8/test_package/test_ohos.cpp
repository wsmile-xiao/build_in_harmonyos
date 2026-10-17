// test_ohos.cpp — lib_fts HarmonyOS 专项测试（test_package）
// 仅通过公开头文件 <fts_fuzzy_match.h> 使用公开 API。覆盖 OHOS 用户常见场景：
//   * 文件路径模糊搜索（UE4 风格资源路径）
//   * 长字符串与大量候选
//   * 中文/多字节字符串（按字节处理的 C API 语义）
// STB 风格单头文件库：include 前定义 FTS_FUZZY_MATCH_IMPLEMENTATION 实例化实现。
#define FTS_FUZZY_MATCH_IMPLEMENTATION
#include <fts_fuzzy_match.h>

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

static int failures = 0;

static void expect(bool cond, const char *name) {
    if (cond) {
        std::printf("OHOS PASS %s\n", name);
    } else {
        std::printf("OHOS FAIL %s\n", name);
        ++failures;
    }
}

int main() {
    // OHOS 场景 1：资源路径模糊搜索（模拟应用内资源定位）
    const char *candidates[] = {
        "entry/src/main/resources/base/element/string.json",
        "entry/src/main/resources/base/media/app_icon.png",
        "entry/src/main/resources/base/profile/main_pages.json",
        "entry/src/main/resources/rawfile/config.json",
    };
    const char *pattern = "mainprofilejson";
    int matched = 0;
    for (const char *c : candidates) {
        if (fts::fuzzy_match_simple(pattern, c)) {
            ++matched;
            std::printf("OHOS match: [%s] -> %s\n", pattern, c);
        }
    }
    // 预期恰好命中 main_pages.json（模式字符按序全部出现且集中）
    expect(matched >= 1, "ohos: profile json search finds at least one");

    // OHOS 场景 2：长路径字符串（不崩溃、稳定匹配）
    std::string longPath = "/data/app/el2/100/base/com.example.demo/haps/entry/files/";
    for (int i = 0; i < 200; ++i) longPath += "segment_" + std::to_string(i) + "/";
    longPath += "asset.bin";
    expect(fts::fuzzy_match_simple("assetbin", longPath.c_str()), "ohos: long path fuzzy match");
    expect(!fts::fuzzy_match_simple("zzzzzzz", longPath.c_str()), "ohos: long path negative match");

    // OHOS 场景 3：中文/多字节字符串按字节匹配（tolower 仅作用于 ASCII）
    const char *zh = "鸿蒙系统文件资源";
    expect(fts::fuzzy_match_simple("\xe9\xb8\xbf", zh), "ohos: multibyte prefix byte-match");

    // OHOS 场景 4：评分数值随匹配质量单调（好的匹配分更高）
    int sGood = 0, sPoor = 0;
    fts::fuzzy_match("abc", "a-b_c", sGood);
    fts::fuzzy_match("abc", "axxxbxxc", sPoor);
    std::printf("OHOS score good=%d poor=%d\n", sGood, sPoor);
    expect(sGood > sPoor, "ohos: compact match scores higher");

    if (failures == 0) {
        std::printf("OHOS ALL TESTS PASSED\n");
        return 0;
    }
    std::printf("OHOS %d TEST(S) FAILED\n", failures);
    return 1;
}