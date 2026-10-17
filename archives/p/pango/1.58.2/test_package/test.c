/* pango 1.58.2 真实功能断言。
 *
 * 核心是第 ③ 条：**泰文断行**。它是 libthai 真接进 pango 的有效判据 ——
 * pango/break-thai.c 里 break_thai() 的函数体**整个包在 #ifdef HAVE_LIBTHAI 内**
 * （26 行 #ifdef 到 123 行 #endif），没有 libthai 就是彻底 no-op、
 * 一个泰文断点都不插。所以「泰文串内部出现断行机会」推得出「libthai 已接入」。
 *
 * 对照本批次另外两种情形，说明为什么每次都得单独查：
 *   · gd + libpng   —— 缺依赖时是**返回 NULL 的空桩** → 编解码往返是有效判据
 *   · hwloc + libxml2 —— 缺依赖时有**能用的**内置实现（nolibxml）→ XML 往返判不了
 *
 * 不用 dlopen 探针：解析到 pango_get_log_attrs 不等于断行真按泰文规则走。
 */
#include <pango/pango.h>
#include <stdio.h>
#include <string.h>

/* "ภาษาไทย"（泰语）= ภาษา(语言) + ไทย(泰)，共 7 个字符。
 * libthai 在第 4 个字符后断词（libthai 那层已单独验过断点 = 4）。
 * 这里用 UTF-8 —— pango 的 API 收 UTF-8，不是 TIS-620。 */
static const char *THAI = "\xe0\xb8\xa0\xe0\xb8\xb2\xe0\xb8\xa9\xe0\xb8\xb2"  /* ภาษา */
                          "\xe0\xb9\x84\xe0\xb8\x97\xe0\xb8\xa2";             /* ไทย  */
#define THAI_CHARS   7
#define THAI_BREAK   4

/* 自己数 UTF-8 字符，**不用 g_utf8_strlen**：
 * test_package 只链被测包的 libs（-lpango-1.0 …），glib 的符号不在链接行里，
 * 用了会 undefined reference —— 这类问题在设备上编译期才炸，不如一开始避开。 */
static int utf8_len(const char *s)
{
    int n = 0;
    for (; *s; s++)
        if ((*s & 0xC0) != 0x80) n++;   /* 非续接字节即一个字符起始 */
    return n;
}

static int test_version(void)
{
    int rt = pango_version();
    const char *vs = pango_version_string();
    printf("pango 运行期 %d (%s) / 编译期宏 %d\n", rt, vs ? vs : "(null)", PANGO_VERSION);
    if (!vs || !*vs) { printf("FAIL pango_version_string 为空\n"); return 1; }
    /* 运行期与编译期不一致 = 头和库不是同一次构建的（包本身的缺陷） */
    if (rt != PANGO_VERSION) {
        printf("FAIL 运行期 %d != 编译期宏 %d（头库错配）\n", rt, PANGO_VERSION);
        return 1;
    }
    return 0;
}

/* PangoLanguage 往返 —— 纯字符串映射，结果是定值 */
static int test_language(void)
{
    PangoLanguage *th = pango_language_from_string("th");
    PangoLanguage *en = pango_language_from_string("en-US");
    const char *s;

    if (!th || !en) { printf("FAIL pango_language_from_string 返回空\n"); return 1; }
    s = pango_language_to_string(th);
    if (!s || strcmp(s, "th") != 0) {
        printf("FAIL language 往返 \"th\" -> \"%s\"\n", s ? s : "(null)"); return 1;
    }
    /* pango 会把 language tag 规范化为小写 */
    s = pango_language_to_string(en);
    if (!s || strcmp(s, "en-us") != 0) {
        printf("FAIL language 往返 \"en-US\" -> \"%s\"，期望 \"en-us\"\n", s ? s : "(null)");
        return 1;
    }
    /* 同一 tag 必须返回同一实例（PangoLanguage 是驻留的） */
    if (pango_language_from_string("th") != th) {
        printf("FAIL 同一 tag 未返回同一 PangoLanguage 实例\n"); return 1;
    }
    printf("PangoLanguage OK: 往返一致、大小写规范化、实例驻留\n");
    return 0;
}

/* 英文断行 —— 不依赖任何可选后端，先确认断行框架本身是好的。
 * 这条是第 ③ 条的对照组：若这条就挂了，说明问题不在 libthai。 */
static int test_break_english(void)
{
    const char *s = "hello world";
    int n = (int)utf8_len(s);
    PangoLogAttr attrs[32];
    int i, word_starts = 0;

    memset(attrs, 0, sizeof attrs);
    pango_get_log_attrs(s, (int)strlen(s), -1,
                        pango_language_from_string("en"), attrs, n + 1);
    for (i = 0; i <= n; i++)
        if (attrs[i].is_word_start) word_starts++;
    /* "hello world" 恰好两个词 */
    if (word_starts != 2) {
        printf("FAIL 英文 \"hello world\" 词首数 %d != 2\n", word_starts); return 1;
    }
    /* 空格处（下标 5）必须是断行机会 */
    if (!attrs[6].is_line_break) {
        printf("FAIL 英文空格后无断行机会\n"); return 1;
    }
    printf("英文断行 OK: 2 个词首、空格处可断\n");
    return 0;
}

/* 泰文断行 —— libthai 接入的判据。
 * 泰文**词间不写空格**，所以串内部若出现断行机会，只可能来自词典断词。 */
static int test_break_thai(void)
{
    int n = (int)utf8_len(THAI);
    PangoLogAttr attrs[32];
    int i, inner_breaks = 0;

    if (n != THAI_CHARS) {
        printf("FAIL 泰文串字符数 %d != %d（UTF-8 字节写错了）\n", n, THAI_CHARS);
        return 1;
    }
    memset(attrs, 0, sizeof attrs);
    pango_get_log_attrs(THAI, (int)strlen(THAI), -1,
                        pango_language_from_string("th"), attrs, n + 1);

    /* 只数**内部**断点（下标 1..n-1）；首尾天然是断点，不算证据 */
    for (i = 1; i < n; i++)
        if (attrs[i].is_line_break) inner_breaks++;

    printf("泰文内部断行机会: %d 处（位置", inner_breaks);
    for (i = 1; i < n; i++) if (attrs[i].is_line_break) printf(" %d", i);
    printf("）\n");

    if (inner_breaks == 0) {
        printf("FAIL 泰文串内部无任何断行机会 —— libthai 未接入 pango。\n");
        printf("     break-thai.c 的 break_thai() 整体在 #ifdef HAVE_LIBTHAI 内，\n");
        printf("     没有 libthai 时是彻底 no-op。检查 meson 的 -Dlibthai=enabled\n");
        printf("     以及 libthai 的 .pc（pango 找的是 dependency('libthai')）。\n");
        return 1;
    }
    /* libthai 把 ภาษาไทย 切成 ภาษา|ไทย，断点应落在第 4 个字符处 */
    if (!attrs[THAI_BREAK].is_line_break) {
        printf("FAIL 期望位置 %d 有断点（ภาษา|ไทย），实际没有\n", THAI_BREAK);
        return 1;
    }
    printf("泰文断行 OK: 位置 %d 可断（ภาษา|ไทย）—— libthai 已接入 pango\n", THAI_BREAK);
    return 0;
}

int main(void)
{
    int passed = 0;
    if (test_version() == 0) passed++;
    if (test_language() == 0) passed++;
    if (test_break_english() == 0) passed++;
    if (test_break_thai() == 0) passed++;
    /* 机器可读汇总行：test_package/conanfile.py 解析它产生 HMBS 标记;数字来自真实执行。 */
    printf("PANGO_TEST total=4 passed=%d\n", passed);
    if (passed != 4) {
        printf("pango 1.58.2: %d/4 用例通过\n", passed);
        return 1;
    }
    printf("pango 1.58.2: 全部断言通过\n");
    return 0;
}
