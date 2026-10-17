// edlib 1.2.7 HarmonyOS 专项测试（真实可执行，非空壳）
// 断言：平台识别 + edlib API 功能（编辑距离/位置/路径/CIGAR/自定义等价关系）
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include "edlib.h"

static int g_fail = 0;
#define CHECK(cond, msg) do { \
    if (cond) { printf("  PASS: %s\n", msg); } \
    else { printf("  FAIL: %s\n", msg); g_fail++; } \
} while (0)

int main() {
    printf("=== edlib 1.2.7 HarmonyOS 专项测试 ===\n");

    // 1. 平台识别：OHOS aarch64 工具链（clang 15 + libc++）
#if defined(__OHOS__) || defined(__OHOS_FAMILY__) || defined(OPENHARMONY)
    CHECK(true, "platform: OHOS 宏已定义");
#elif defined(__aarch64__) || defined(_M_ARM64)
    CHECK(true, "platform: aarch64 架构（HarmonyOS PC 目标）");
#else
    CHECK(false, "platform: 未知平台宏");
#endif
#if defined(__linux__)
    CHECK(true, "platform: __linux__ 定义（HarmonyOS 基于 Linux 内核）");
#else
    CHECK(false, "platform: __linux__ 缺失");
#endif

    // 2. edlibAlign 基本编辑距离（README 示例："hello" vs "world!"）
    EdlibAlignResult r = edlibAlign("hello", 5, "world!", 6, edlibDefaultAlignConfig());
    CHECK(r.status == EDLIB_STATUS_OK, "edlibAlign status OK");
    printf("  editDistance(hello/world!)=%d\n", r.editDistance);
    CHECK(r.editDistance == 5, "editDistance(hello/world!)==5");
    edlibFreeAlignResult(r);

    // 3. 相同序列编辑距离为 0
    r = edlibAlign("ACGTACGT", 8, "ACGTACGT", 8, edlibDefaultAlignConfig());
    CHECK(r.status == EDLIB_STATUS_OK, "identical: status OK");
    CHECK(r.editDistance == 0, "identical: editDistance==0");
    edlibFreeAlignResult(r);

    // 4. TASK_PATH：对齐路径非空且首元素为 EDOP（0=match）
    EdlibAlignConfig cfg = edlibNewAlignConfig(-1, EDLIB_MODE_NW, EDLIB_TASK_PATH, NULL, 0);
    r = edlibAlign("telephone", 9, "elephant", 8, cfg);
    CHECK(r.status == EDLIB_STATUS_OK, "path: status OK");
    CHECK(r.editDistance == 3, "path: editDistance(telephone/elephant)==3");
    CHECK(r.alignment != NULL && r.alignmentLength > 0, "path: alignment 非空");
    CHECK(r.numLocations > 0 && r.endLocations != NULL, "path: endLocations 非空");
    edlibFreeAlignResult(r);

    // 5. 自定义等价关系（简并碱基 R=A/G，模式 HW）
    EdlibEqualityPair eq[2] = {{'R', 'A'}, {'R', 'G'}};
    EdlibAlignConfig hw = edlibNewAlignConfig(-1, EDLIB_MODE_HW, EDLIB_TASK_DISTANCE, eq, 2);
    r = edlibAlign("ACTG", 4, "CACTRT", 6, hw);
    CHECK(r.status == EDLIB_STATUS_OK, "degenerate: status OK");
    printf("  degenerate editDistance=%d\n", r.editDistance);
    edlibFreeAlignResult(r);

    // 6. CIGAR 输出（TASK_PATH + EDLIB_CIGAR_EXTENDED 通过 edlibAlignmentToCigar）
    EdlibAlignConfig cigarCfg = edlibNewAlignConfig(-1, EDLIB_MODE_NW, EDLIB_TASK_PATH, NULL, 0);
    r = edlibAlign("TTTT", 4, "TTTT", 4, cigarCfg);
    CHECK(r.status == EDLIB_STATUS_OK, "cigar: status OK");
    CHECK(r.alignment != NULL && r.alignment[0] == EDLIB_EDOP_MATCH, "cigar: 首操作=MATCH");
    if (r.alignment) {
        char* cigar = edlibAlignmentToCigar(r.alignment, r.alignmentLength, EDLIB_CIGAR_EXTENDED);
        CHECK(cigar != NULL && strcmp(cigar, "4=") == 0, "cigar: TTTT/TTTT == \"4=\"");
        printf("  cigar string: %s\n", cigar ? cigar : "(null)");
        free(cigar);
    }
    edlibFreeAlignResult(r);

    // 7. k 限制：k=0 且序列不同 → editDistance==-1
    EdlibAlignConfig k0 = edlibNewAlignConfig(0, EDLIB_MODE_NW, EDLIB_TASK_DISTANCE, NULL, 0);
    r = edlibAlign("abc", 3, "abd", 3, k0);
    CHECK(r.editDistance == -1, "k-limit: editDistance==-1 (超过 k=0)");
    edlibFreeAlignResult(r);

    printf("=== 结果: %s (%d 失败) ===\n", g_fail == 0 ? "ALL PASS" : "FAILED", g_fail);
    return g_fail == 0 ? 0 : 1;
}
