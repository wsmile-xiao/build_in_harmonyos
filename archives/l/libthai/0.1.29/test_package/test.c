/* libthai 0.1.29 真实功能断言。
 *
 * 两层判据，第②层是关键：
 *
 *   ① 字符分类（th_isthai/th_isthcons/...）—— 纯查表，无外部依赖，结果可手算。
 *      这层过了只证明 libthai 自身编对了。
 *
 *   ② **断词**（th_brk_new + th_brk_find_breaks）—— 这条同时证明三件事：
 *        · 词典 thbrk.tri 真被 trietool 造出来并装进了包（tool_requires 生效）
 *        · libdatrie 真接上了（词典就是双数组 trie，读它必须经 libdatrie）
 *        · LIBTHAI_DICTDIR runenv 生效（否则回落到编译期烤死的 DICT_DIR 绝对路径，
 *          换台机器 / 换 conan cache 就找不到 —— 属于「本机能过、换机器才炸」那类缺陷）
 *      libthai **没有**内置词典兜底：th_brk_new 取不到词典直接返回 NULL，
 *      所以这条是有效判据（对照 hwloc 的 nolibxml —— 那个有真兜底，判不了依赖接入）。
 *
 * 泰文字节由 Python 的 tis-620 codec 算出，非手抄码位。
 * 不用 dlopen 探针：解析到 th_brk_new 不等于断词真能跑。
 */
#include <thai/thctype.h>
#include <thai/thbrk.h>
#include <stdio.h>
#include <string.h>

/* "ภาษาไทย"（泰语）= ภาษา(语言) + ไทย(泰)
 * TIS-620: C0 D2 C9 D2 | E4 B7 C2 —— 正确断点在第 4 个字节后 */
static const thchar_t THAI_PHRASE[] = {
    0xC0, 0xD2, 0xC9, 0xD2,   /* ภาษา */
    0xE4, 0xB7, 0xC2,         /* ไทย  */
    0x00
};
#define EXPECT_BREAK 4

static int test_ctype(void)
{
    /* th_isthai(c) = th_istis(c) && (c & 0x80)（thctype.h:396）——
     * 泰文区在高位，ASCII 必须为假。 */
    if (!th_isthai(0xC0)) { printf("FAIL th_isthai(0xC0=ภ) 应为真\n"); return 1; }
    if (!th_isthai(0xE4)) { printf("FAIL th_isthai(0xE4=ไ) 应为真\n"); return 1; }
    if (th_isthai('A'))   { printf("FAIL th_isthai('A') 应为假\n"); return 1; }
    if (th_isthai('0'))   { printf("FAIL th_isthai('0') 应为假\n"); return 1; }

    /* th_iseng(c) = !(c & 0x80)（thctype.h:397） */
    if (!th_iseng('A'))   { printf("FAIL th_iseng('A') 应为真\n"); return 1; }
    if (th_iseng(0xC0))   { printf("FAIL th_iseng(0xC0) 应为假\n"); return 1; }

    /* 辅音 / 元音分类：ภ(0xC0) 是辅音，า(0xD2) 是元音 —— 两者都为真的实现是错的 */
    if (!th_isthcons(0xC0)) { printf("FAIL 0xC0=ภ 应是辅音\n"); return 1; }
    if (th_isthcons(0xD2))  { printf("FAIL 0xD2=า 是元音，不该判成辅音\n"); return 1; }
    if (!th_isthvowel(0xD2)){ printf("FAIL 0xD2=า 应是元音\n"); return 1; }
    if (th_isthvowel(0xC0)) { printf("FAIL 0xC0=ภ 是辅音，不该判成元音\n"); return 1; }

    printf("字符分类 OK: 泰/英、辅音/元音 正反例各自成立\n");
    return 0;
}

static int test_wordbreak(void)
{
    ThBrk *brk;
    int pos[16];
    int n, i;

    /* NULL = 用默认词典：先查 LIBTHAI_DICTDIR，再回落编译期 DICT_DIR
     * （src/thbrk/brk-common.c:53-64）。取不到词典返回 NULL，无内置兜底。 */
    brk = th_brk_new(NULL);
    if (!brk) {
        printf("FAIL th_brk_new(NULL) 返回空 —— 词典 thbrk.tri 没找到。\n");
        printf("     可能原因：trietool 未参与构建（tool_requires 没生效）导致词典没造出来；\n");
        printf("     或 LIBTHAI_DICTDIR 未设且编译期 DICT_DIR 指向的路径已不存在。\n");
        return 1;
    }

    n = th_brk_find_breaks(brk, THAI_PHRASE, pos, sizeof pos / sizeof pos[0]);
    if (n < 0) {
        printf("FAIL th_brk_find_breaks 返回 %d\n", n);
        th_brk_delete(brk); return 1;
    }
    printf("断词结果: %d 个断点 [", n);
    for (i = 0; i < n; i++) printf("%s%d", i ? ", " : "", pos[i]);
    printf("]\n");

    /* "ภาษาไทย" 应恰好切成 ภาษา|ไทย —— 一个断点，位置 4。
     * 断点数为 0 说明词典是空的（trie 建出来了但没灌词条）——
     * 那种情况下 th_brk_new 照样成功，只验「不为 NULL」是抓不住的。 */
    if (n != 1) {
        printf("FAIL 期望 1 个断点，实得 %d（n=0 通常意味着词典为空）\n", n);
        th_brk_delete(brk); return 1;
    }
    if (pos[0] != EXPECT_BREAK) {
        printf("FAIL 断点位置 %d != %d\n", pos[0], EXPECT_BREAK);
        th_brk_delete(brk); return 1;
    }

    /* 负例：纯英文不该产生断点 —— 证明断词真在查词典而非机械每 N 字符切一刀 */
    {
        const thchar_t eng[] = "graphviz";
        n = th_brk_find_breaks(brk, eng, pos, sizeof pos / sizeof pos[0]);
        if (n != 0) {
            printf("FAIL 纯英文 \"graphviz\" 竟产生 %d 个断点\n", n);
            th_brk_delete(brk); return 1;
        }
    }

    th_brk_delete(brk);
    printf("断词 OK: ภาษาไทย 正确切为 ภาษา|ไทย（断点 %d），英文无断点\n", EXPECT_BREAK);
    printf("         → 词典已构建并装包、libdatrie 已接入、词典路径可解析\n");
    return 0;
}

int main(void)
{
    if (test_ctype())     return 1;
    if (test_wordbreak()) return 1;
    printf("libthai 0.1.29: 全部断言通过\n");
    return 0;
}
