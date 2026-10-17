/* HarmonyOS 专项测试 — libuninameslist 20250714 (OHOS aarch64)
 *
 * 验证当前库在 OHOS 平台上经公开头文件 + 公开 API 链接、调用、运行正常，
 * 并校验数据完整性（Unicode 块连续性、版本常量、名称/块查询、names2 别名表）。
 * 仅使用安装产物（uninameslist.h + libuninameslist）。
 */
#include <stdio.h>
#include <string.h>
#include <uninameslist.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (cond) { printf("PASS: %s\n", msg); } \
    else { printf("FAIL: %s\n", msg); failures++; } \
} while (0)

int main(void) {
    /* 1. 版本常量 */
    const char *ver = uniNamesList_NamesListVersion();
    printf("NamesListVersion = %s\n", ver ? ver : "(null)");
    CHECK(ver && strstr(ver, "16.0") != NULL, "版本为 Nameslist 16.0");

    /* 2. 块总数与 UnicodeBlock 数组一致 */
    int nb = uniNamesList_blockCount();
    printf("blockCount = %d, UNICODE_BLOCK_MAX = %d\n", nb, UNICODE_BLOCK_MAX);
    CHECK(nb == 361 && nb == UNICODE_BLOCK_MAX, "块数 == 361 == UNICODE_BLOCK_MAX");

    /* 3. 数据完整性：361 块有序且两两不重叠（NamesList 仅覆盖已命名区间，
     *    未分配区间即块间隙，块与块之间允许 gap）*/
    int ordered = 1;
    long prev_end = -1;
    for (int i = 0; i < nb; i++) {
        long s = uniNamesList_blockStart(i);
        long e = uniNamesList_blockEnd(i);
        if (s < 0 || e < s) { ordered = 0; break; }
        if (i > 0 && s <= prev_end) { ordered = 0; break; }
        prev_end = e;
    }
    CHECK(ordered == 1, "361 个 Unicode 块有序且非重叠");

    /* 4. 名称查询：U+0041 / U+1F600（emoji，载于 NamesList 表）*/
    const char *nA = uniNamesList_name(0x41UL);
    const char *nEmoji = uniNamesList_name(0x1F600UL);
    printf("name(0x41)=%s  name(0x1F600)=%s\n", nA ? nA : "(null)", nEmoji ? nEmoji : "(null)");
    CHECK(nA && strcmp(nA, "LATIN CAPITAL LETTER A") == 0, "name(U+0041) == LATIN CAPITAL LETTER A");
    CHECK(nEmoji && strcmp(nEmoji, "GRINNING FACE") == 0, "name(U+1F600) == GRINNING FACE");
    CHECK(uniNamesList_name(0x4E00UL) == NULL,
          "name(U+4E00) == NULL（CJK 表意文字不在 NamesList 名称表，符合上游数据）");

    /* 5. 块查询往返：U+0041 → 块 0（Basic Latin）*/
    int bn = uniNamesList_blockNumber(0x41UL);
    const char *bname = bn >= 0 ? uniNamesList_blockName(bn) : NULL;
    printf("blockNumber(0x41)=%d blockName=%s\n", bn, bname ? bname : "(null)");
    CHECK(bn == 0 && bname && strstr(bname, "Basic Latin") != NULL, "U+0041 属于 Basic Latin 块");

    /* 6. names2 别名表（20200413+ API）*/
    int n2 = uniNamesList_names2cnt();
    printf("names2cnt = %d\n", n2);
    CHECK(n2 > 0, "names2 别名表非空");
    if (n2 > 0) {
        long v0 = uniNamesList_names2val(0);
        CHECK(v0 >= 0, "names2[0] 有效码点");
    }

    /* 7. 语言接口（英文库）：Languages(0) 返回 "EN" */
    const char *l0 = uniNamesList_Languages(0);
    printf("Languages(0) = %s\n", l0 ? l0 : "(null)");
    CHECK(l0 && strcmp(l0, "EN") == 0, "Languages(0) == EN");

    if (failures == 0) {
        printf("OHOS_TEST: ALL 7 CHECKS PASSED\n");
        return 0;
    }
    printf("OHOS_TEST: %d CHECK(S) FAILED\n", failures);
    return 1;
}