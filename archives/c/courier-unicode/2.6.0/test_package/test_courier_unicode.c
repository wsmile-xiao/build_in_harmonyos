/* Consumer test for courier-unicode 2.6.0.
 *
 * Builds against the packaged courier-unicode library and exercises 14
 * real API assertions covering case mapping, HTML entities, character
 * classes, widths, general categories and the default charset query.
 * Any failure exits non-zero so `conan create` fails.
 */
#include <courier-unicode.h>
#include <stdio.h>

static int g_passed = 0;

#define CHECK(cond, name) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s\n", name); \
        return 1; \
    } \
    printf("PASS: %s\n", name); \
    g_passed++; \
} while (0)

int main(void)
{
    /* 1-3: case mapping */
    CHECK(unicode_uc((char32_t)'a') == (char32_t)'A', "unicode_uc a->A");
    CHECK(unicode_lc((char32_t)'A') == (char32_t)'a', "unicode_lc A->a");
    CHECK(unicode_tc((char32_t)'a') == (char32_t)'A', "unicode_tc a->A");

    /* 4-5: HTML entity lookup (named + numeric, cf. upstream enttest.c) */
    CHECK(unicode_html40ent_lookup("amp") == (char32_t)38, "html amp==38");
    CHECK(unicode_html40ent_lookup("#65") == (char32_t)65, "html numeric #65==65");

    /* 6-11: character classes (cf. upstream enttest.c category checks) */
    CHECK(unicode_isalpha((char32_t)'A'), "isalpha A");
    CHECK(unicode_isdigit((char32_t)'0'), "isdigit 0");
    CHECK(unicode_isspace((char32_t)' '), "isspace space");
    CHECK(unicode_ispunct((char32_t)'['), "ispunct [");
    CHECK(unicode_islower((char32_t)'a') && !unicode_islower((char32_t)'A'), "islower a not A");
    CHECK(unicode_isupper((char32_t)'A'), "isupper A");

    /* 12: console width of a plain Latin letter is 1 per tr11 docs */
    CHECK(unicode_wcwidth((char32_t)'A') == 1, "wcwidth A==1");

    /* 13: general category of 'A' is uppercase letter */
    CHECK(unicode_general_category_lookup((char32_t)0x41) == UNICODE_GENERAL_CATEGORY_Lu,
          "general category A==Lu");

    /* 14: default charset query is always non-NULL */
    CHECK(unicode_default_chset() != 0 && unicode_default_chset()[0] != '\0',
          "default chset non-empty");

    printf("All %d courier-unicode consumer checks passed.\n", g_passed);
    return g_passed == 14 ? 0 : 1;
}
