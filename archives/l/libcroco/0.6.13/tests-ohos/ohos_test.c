/* OHOS 专项测试：通过公开 API 解析 CSS 并核验可观察结果
 * （与上游 testctl 测试、test_package 消费者用例分别计数）
 * 验证点：cr_om_parser_simply_parse_buf 解析 → cr_stylesheet_nr_rules 计数
 *          → cr_stylesheet_to_string 序列化非空且含规则 → 回收
 */
#include <glib.h>
#include <libcroco/libcroco.h>

int main(void)
{
    const guchar css[] =
        "h1 { color: #990033; margin: 0px; }\n"
        "p.commentsbody { font-size: 12px; line-height: 1.3em; }";
    CRStyleSheet *sheet = NULL;
    enum CRStatus status =
        cr_om_parser_simply_parse_buf(css, sizeof(css) - 1, CR_UTF_8, &sheet);

    if (status != CR_OK || sheet == NULL) {
        g_printerr("OHOS test: parse failed status=%d\n", (int)status);
        return 1;
    }

    gint n_rules = cr_stylesheet_nr_rules(sheet);
    if (n_rules != 2) {
        g_printerr("OHOS test: expected 2 rules, got %d\n", n_rules);
        cr_stylesheet_destroy(sheet);
        return 2;
    }

    gchar *css_out = cr_stylesheet_to_string(sheet);
    if (css_out == NULL || !g_strstr_len(css_out, -1, "h1")) {
        g_printerr("OHOS test: serialized output missing selector\n");
        g_free(css_out);
        cr_stylesheet_destroy(sheet);
        return 3;
    }
    g_free(css_out);
    cr_stylesheet_destroy(sheet);
    return 0;
}
