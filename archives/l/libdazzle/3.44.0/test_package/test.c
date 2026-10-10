#include <stdio.h>
#include <string.h>

#include <glib.h>
#include <glib-object.h>

#include "dazzle.h"
#include "search/dzl-pattern-spec.h"
#include "search/dzl-levenshtein.h"

/*
 * libdazzle 3.44.0 消费者端到端测试（HarmonyOS PC aarch64）。
 * 真实消费公开 API（无显示依赖的子集）：模糊搜索 pattern spec + Levenshtein 距离，
 * 全部为断言型用例，覆盖「include 头 → GObject 类型系统 → 库符号 → 行为正确性」链路。
 */

static int g_failures = 0;
static int g_total = 0;

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        g_total++;                                                           \
        if (cond) {                                                          \
            printf("PASS: %s\n", msg);                                       \
        } else {                                                             \
            printf("FAIL: %s\n", msg);                                       \
            g_failures++;                                                    \
        }                                                                    \
    } while (0)

static void
test_gobject_type_registration (void)
{
    /* DzlPatternSpec 是 boxed 类型；get_type() 触发类型注册，
     * 验证库与 gobject 运行时链接正确。 */
    GType type = dzl_pattern_spec_get_type ();

    CHECK (type != G_TYPE_INVALID, "dzl_pattern_spec_get_type registers a GType");
    CHECK (g_type_is_a (type, G_TYPE_BOXED), "DzlPatternSpec is a boxed GType");
}

static void
test_pattern_spec_basic (void)
{
    g_autoptr(DzlPatternSpec) spec = dzl_pattern_spec_new ("dzl pat");

    CHECK (spec != NULL, "dzl_pattern_spec_new returns a spec");
    CHECK (g_strcmp0 (dzl_pattern_spec_get_text (spec), "dzl pat") == 0,
           "dzl_pattern_spec_get_text round-trips the keyword");
    /* DzlPatternSpec 语义：关键词按空白分词，每个词须为 haystack 中
     * 某个分隔符切分 token 的前缀（不区分大小写）；无驼峰切分。 */
    CHECK (dzl_pattern_spec_match (spec, "dzl-pattern-spec.c"),
           "dzl_pattern_spec_match hits 'dzl-pattern-spec.c'");
    CHECK (dzl_pattern_spec_match (spec, "src/widgets/dzl-pattern-bin.c"),
           "dzl_pattern_spec_match hits multi-token path with both words");
    CHECK (!dzl_pattern_spec_match (spec, "pattern-spec.c"),
           "dzl_pattern_spec_match rejects haystack missing the 'dzl' word");
    CHECK (!dzl_pattern_spec_match (spec, "gtk-widget.c"),
           "dzl_pattern_spec_match rejects unrelated 'gtk-widget.c'");
}

static void
test_pattern_spec_single_word (void)
{
    g_autoptr(DzlPatternSpec) spec = dzl_pattern_spec_new ("pattern");

    CHECK (dzl_pattern_spec_match (spec, "dzl-pattern-spec.c"),
           "single-word spec hits token prefix 'pattern'");
    CHECK (!dzl_pattern_spec_match (spec, "dzl-levenshtein.c"),
           "single-word spec rejects haystack without matching token");
}

static void
test_pattern_spec_lifecycle (void)
{
    DzlPatternSpec *spec = dzl_pattern_spec_new ("levenshtein");
    DzlPatternSpec *ref = dzl_pattern_spec_ref (spec);

    CHECK (ref == spec, "dzl_pattern_spec_ref returns same instance");
    dzl_pattern_spec_unref (ref);
    dzl_pattern_spec_unref (spec);
    CHECK (1, "ref/unref lifecycle completes without crash");
}

static void
test_levenshtein_distance (void)
{
    CHECK (dzl_levenshtein ("abc", "abc") == 0,
           "dzl_levenshtein identical strings == 0");
    CHECK (dzl_levenshtein ("abc", "abd") == 1,
           "dzl_levenshtein one substitution == 1");
    CHECK (dzl_levenshtein ("kitten", "sitting") == 3,
           "dzl_levenshtein kitten/sitting == 3");
    CHECK (dzl_levenshtein ("abc", "") == 3,
           "dzl_levenshtein empty haystack == needle length");
}

int
main (int argc, char *argv[])
{
    printf ("libdazzle consumer test (HarmonyOS PC aarch64)\n");
    test_gobject_type_registration ();
    test_pattern_spec_basic ();
    test_pattern_spec_single_word ();
    test_pattern_spec_lifecycle ();
    test_levenshtein_distance ();

    printf ("---\n");
    if (g_failures > 0) {
        printf ("RESULT: FAIL (%d/%d assertion(s) failed)\n", g_failures, g_total);
        return 1;
    }
    printf ("RESULT: PASS (%d/%d assertions)\n", g_total, g_total);
    return 0;
}
