#include <glib.h>
#include <libcroco/libcroco.h>

int main(void)
{
    /* 公开 API：用 cr_om_parser_simply_parse_buf 解析一段内联 CSS，
     * 验证第三方消费者可编译、链接 libcroco-0.6 并通过
     * cr_stylesheet_nr_rules 得到可观察结果。 */
    const guchar css[] = "body { color: red; margin: 0; }";
    CRStyleSheet *sheet = NULL;
    enum CRStatus status =
        cr_om_parser_simply_parse_buf(css, sizeof(css) - 1, CR_UTF_8, &sheet);
    if (status != CR_OK || sheet == NULL) {
        return 1;
    }
    gint n_rules = cr_stylesheet_nr_rules(sheet);
    if (n_rules < 0) {
        cr_stylesheet_destroy(sheet);
        return 2;
    }
    gchar *css_out = cr_stylesheet_to_string(sheet);
    if (css_out == NULL) {
        cr_stylesheet_destroy(sheet);
        return 3;
    }
    g_free(css_out);
    cr_stylesheet_destroy(sheet);
    return 0;
}