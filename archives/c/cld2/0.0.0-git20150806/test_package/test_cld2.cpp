// Consumer test for cld2: DetectLanguageSummary on English and French text.
// Usage: ./test_cld2 [english|french]  (no arg runs both cases)
#include <cstdio>
#include <cstring>
#include <string>

#include "compact_lang_det.h"

static const char* kEnglish =
    "confiscation of goods is assigned as the penalty part most of the courts "
    "consist of members and when it is necessary to bring public cases before "
    "a jury of members two courts combine for the purpose the most important "
    "cases of all are brought before the jurors and the verdict of the jury "
    "determines the outcome of the trial under the law of the land";

static const char* kFrench =
    "la confiscation des biens est prononcee comme peine par la plupart des "
    "tribunaux qui sont composes de membres et lorsqu il est necessaire de "
    "porter les affaires publiques devant un jury les deux juridictions se "
    "reunissent a cette fin les affaires les plus importantes sont portees "
    "devant les jures et le verdict du jury determine l issue du proces";

static int run_case(const char* name, const char* text, CLD2::Language expect) {
    CLD2::Language language3[3];
    int percent3[3];
    int text_bytes = 0;
    bool is_reliable = false;
    CLD2::Language lang = CLD2::DetectLanguageSummary(
        text, static_cast<int>(strlen(text)), true,
        language3, percent3, &text_bytes, &is_reliable);
    std::printf("[%s] detected=%d expected=%d reliable=%d text_bytes=%d "
                "percent0=%d\n",
                name, static_cast<int>(lang), static_cast<int>(expect),
                is_reliable ? 1 : 0, text_bytes, percent3[0]);
    if (text_bytes <= 0) {
        std::printf("[%s] FAIL: no text bytes classified\n", name);
        return 1;
    }
    if (lang != expect || language3[0] != expect) {
        std::printf("[%s] FAIL: wrong language\n", name);
        return 1;
    }
    std::printf("[%s] PASS\n", name);
    return 0;
}

int main(int argc, char** argv) {
    std::string only = argc > 1 ? argv[1] : "all";
    int rc = 0;
    int discovered = 0;
    int passed = 0;
    if (only == "all" || only == "english") {
        ++discovered;
        if (run_case("english", kEnglish, CLD2::ENGLISH) == 0) ++passed;
        else rc = 1;
    }
    if (only == "all" || only == "french") {
        ++discovered;
        if (run_case("french", kFrench, CLD2::FRENCH) == 0) ++passed;
        else rc = 1;
    }
    if (only == "all") {
        std::printf("test_cld2: %d/%d cases passed\n", passed, discovered);
    }
    // HMBS machine marker: always emit so every invocation mode
    // (./test_cld2, ./test_cld2 english, ./test_cld2 french as run by
    // ctest) carries discovered/passedCount evidence.
    std::printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,"
                "\"passed\":%s,\"command\":\"./test_cld2 %s\","
                "\"discovered\":%d,\"passedCount\":%d}\n",
                rc == 0 ? "true" : "false", only.c_str(),
                discovered, passed);
    return rc;
}
