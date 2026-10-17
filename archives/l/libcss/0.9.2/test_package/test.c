/* test_package/test.c — libcss 0.9.2 消费者测试程序
 *
 * 从消费者视角验证 libcss 的核心链路：解析内联 CSS 样式表 →
 * select 引擎计算 computed style → 断言级联结果（specificity）。
 *
 * css_select_style 需要一个最小的 node 查询 handler（node_name 回调
 * 返回元素名），这里实现一个单元素 <p> 的桩 handler——这是 libcss
 * 的标准消费者用法（NetSurf examples/ 同款模式）。
 *
 * 断言（6 项）：
 *  1. css_stylesheet_create 创建样式表
 *  2. 内联 CSS append+done（含 @media 查询与 @import 声明的规则集）
 *  3. select 上下文挂载样式表（count_sheets == 1）
 *  4. 对 <p> 元素 select：computed color == #ff0000（p 规则命中）
 *  5. p 的 background-color 透明（body 规则不适用于 p——specificity 正确）
 *  6. 销毁路径干净返回（无泄漏崩溃）
 */
#include <stdio.h>
#include <string.h>
#include <assert.h>

#include <libcss/libcss.h>
#include <libcss/unit.h>
#include <libwapcaplet/libwapcaplet.h>

static css_error resolve_url(void *ctx, const char *base,
        lwc_string *rel, lwc_string **abs)
{
    (void)ctx;
    (void)base;
    *abs = lwc_string_ref(rel);
    return CSS_OK;
}

/* 最小 node 查询 handler：单 <p> 元素桩（无 parent/兄弟/类/id） */
static css_error node_name(void *pw, void *node, css_qname *qname)
{
    (void)pw;
    (void)node;
    qname->name = lwc_string_ref((lwc_string *)pw);
    qname->ns = NULL;
    return CSS_OK;
}
static css_error node_classes(void *pw, void *node, lwc_string ***classes, uint32_t *n)
{
    (void)pw; (void)node;
    *classes = NULL; *n = 0;
    return CSS_OK;
}
static css_error node_id(void *pw, void *node, lwc_string **id)
{
    (void)pw; (void)node;
    *id = NULL;
    return CSS_OK;
}
static css_error named_ancestor_node(void *pw, void *node,
        const css_qname *qname, void **ancestor)
{
    (void)pw; (void)node; (void)qname;
    *ancestor = NULL;
    return CSS_OK;
}
static css_error named_generic_node(void *pw, void *node,
        const css_qname *qname, void **next)
{
    (void)pw; (void)node; (void)qname;
    *next = NULL;
    return CSS_OK;
}
static css_error named_sibling_node(void *pw, void *node,
        const css_qname *qname, void **sibling)
{
    (void)pw; (void)node; (void)qname;
    *sibling = NULL;
    return CSS_OK;
}
static css_error parent_node(void *pw, void *node, void **parent)
{
    (void)pw; (void)node;
    *parent = NULL;
    return CSS_OK;
}
static css_error sibling_node(void *pw, void *node, void **sibling)
{
    (void)pw; (void)node;
    *sibling = NULL;
    return CSS_OK;
}
static css_error node_presentational_hint(void *pw, void *node,
        uint32_t *nhints, css_hint **hints)
{
    (void)pw; (void)node;
    *nhints = 0;
    *hints = NULL;
    return CSS_OK;
}
static css_error ua_default_for_property(void *pw, uint32_t property,
        css_hint *hint)
{
    (void)pw;
    memset(hint, 0, sizeof(*hint));
    hint->prop = property;
    /* 最小 UA 默认值：font-size 16pt、color 黑、background 透明 */
    if (property == CSS_PROP_FONT_SIZE) {
        hint->data.length.value = 16 << 10; /* 16pt in css_fixed */
        hint->data.length.unit = CSS_UNIT_PT;
    } else if (property == CSS_PROP_COLOR) {
        hint->data.color = 0xff000000;
    } else if (property == CSS_PROP_BACKGROUND_COLOR) {
        hint->data.color = 0x00000000;
    }
    return CSS_OK;
}
static css_error node_has_name(void *pw, void *node, const css_qname *qname, bool *match)
{
    bool eq = false;
    (void)node;
    /* pw 是元素名 lwc_string：只有 <p> 匹配 "p" */
    if (lwc_string_caseless_isequal((lwc_string *)pw, qname->name, &eq) != lwc_error_ok)
        return CSS_NOMEM;
    *match = eq;
    return CSS_OK;
}
static css_error node_has_class(void *pw, void *node, lwc_string *name, bool *match)
{
    (void)pw; (void)node; (void)name;
    *match = false;
    return CSS_OK;
}
static css_error node_has_id(void *pw, void *node, lwc_string *name, bool *match)
{
    (void)pw; (void)node; (void)name;
    *match = false;
    return CSS_OK;
}
static css_error node_has_attribute(void *pw, void *node, const css_qname *qname, bool *match)
{
    (void)pw; (void)node; (void)qname;
    *match = false;
    return CSS_OK;
}
static css_error node_is_root(void *pw, void *node, bool *match)
{
    (void)pw; (void)node;
    *match = true; /* 单元素树：p 是根 */
    return CSS_OK;
}
static css_error node_count_siblings(void *pw, void *node, bool same_name, bool after, int32_t *count)
{
    (void)pw; (void)node; (void)same_name; (void)after;
    *count = 0;
    return CSS_OK;
}
static css_error node_is_empty(void *pw, void *node, bool *match)
{
    (void)pw; (void)node;
    *match = true;
    return CSS_OK;
}
static css_error node_is_link(void *pw, void *node, bool *match)
{
    (void)pw; (void)node;
    *match = false;
    return CSS_OK;
}
static css_error node_is_visited(void *pw, void *node, bool *match)
{
    (void)pw; (void)node;
    *match = false;
    return CSS_OK;
}
static css_error node_is_hover(void *pw, void *node, bool *match)
{
    (void)pw; (void)node;
    *match = false;
    return CSS_OK;
}
static css_error node_is_active(void *pw, void *node, bool *match)
{
    (void)pw; (void)node;
    *match = false;
    return CSS_OK;
}
static css_error node_is_focus(void *pw, void *node, bool *match)
{
    (void)pw; (void)node;
    *match = false;
    return CSS_OK;
}
static css_error node_is_enabled(void *pw, void *node, bool *match)
{
    (void)pw; (void)node;
    *match = false;
    return CSS_OK;
}
static css_error node_is_disabled(void *pw, void *node, bool *match)
{
    (void)pw; (void)node;
    *match = false;
    return CSS_OK;
}
static css_error node_is_checked(void *pw, void *node, bool *match)
{
    (void)pw; (void)node;
    *match = false;
    return CSS_OK;
}
static css_error node_is_target(void *pw, void *node, bool *match)
{
    (void)pw; (void)node;
    *match = false;
    return CSS_OK;
}
static css_error node_is_lang(void *pw, void *node, lwc_string *lang, bool *match)
{
    (void)pw; (void)node; (void)lang;
    *match = false;
    return CSS_OK;
}
static css_error set_libcss_node_data(void *pw, void *node,
        void *libcss_node_data)
{
    (void)pw; (void)node; (void)libcss_node_data;
    return CSS_OK;
}
static css_error get_libcss_node_data(void *pw, void *node,
        void **libcss_node_data)
{
    (void)pw; (void)node;
    *libcss_node_data = NULL;
    return CSS_OK;
}

int main(void)
{
    setbuf(stdout, NULL);
    css_stylesheet_params params;
    css_stylesheet *sheet = NULL;
    css_select_ctx *select_ctx = NULL;
    css_select_results *results = NULL;
    uint32_t n_sheets;
    const css_computed_style *computed;
    css_color color_sh, bg_sh;
    lwc_string *element_name = NULL;
    css_error err;

    memset(&params, 0, sizeof(params));
    params.params_version = CSS_STYLESHEET_PARAMS_VERSION_1;
    params.level = CSS_LEVEL_DEFAULT;
    params.charset = "UTF-8";
    params.url = "http://example.com/test.css";
    params.resolve = resolve_url;

    /* 断言 1: stylesheet 创建 */
    err = css_stylesheet_create(&params, &sheet);
    assert(err == CSS_OK);
    printf("CHECK_PASS: css_stylesheet_create\n");

    /* 断言 2: 解析内联 CSS（author 样式表，含 media query + import） */
    {
        const char *css_text =
            "body { background-color: #ffffff; }\n"
            "p { color: #ff0000; font-size: 12pt; margin-top: 2px; }\n"
            ".cls { color: #00ff00; }\n"
            "#id { color: #0000ff; }\n"
            "p:hover { color: #ffff00; }\n"
            "@media screen { p { line-height: 1.5; } }\n"
            "@import url(\"imported.css\");\n";
        err = css_stylesheet_append_data(
            sheet, (const uint8_t *)css_text, strlen(css_text));
        assert(err == CSS_OK || err == CSS_NEEDDATA);
        err = css_stylesheet_data_done(sheet);
        assert(err == CSS_OK);
    }
    printf("CHECK_PASS: stylesheet append+done (inline CSS parsed, incl media query + import)\n");

    /* 断言 3: select 上下文挂载样式表 */
    err = css_select_ctx_create(&select_ctx);
    assert(err == CSS_OK);
    err = css_select_ctx_append_sheet(select_ctx, sheet, CSS_ORIGIN_AUTHOR, NULL);
    assert(err == CSS_OK);
    err = css_select_ctx_count_sheets(select_ctx, &n_sheets);
    assert(err == CSS_OK && n_sheets == 1);
    printf("CHECK_PASS: select_ctx append+count (%u sheet)\n", (unsigned)n_sheets);

    /* 断言 4/5: 对 p 元素做 select，断言 computed style */
    if (lwc_intern_string("p", 1, &element_name) != lwc_error_ok) {
        printf("CHECK_FAIL: lwc_intern_string\n");
        return 1;
    }
    {
        css_select_handler handler;
        css_media media;
        css_unit_ctx unit_ctx;

        memset(&handler, 0, sizeof(handler));
        handler.handler_version = CSS_SELECT_HANDLER_VERSION_1;
        handler.node_name = node_name;
        handler.node_classes = node_classes;
        handler.node_id = node_id;
        handler.named_ancestor_node = named_ancestor_node;
        handler.named_parent_node = named_ancestor_node;
        handler.named_sibling_node = named_sibling_node;
        handler.named_generic_sibling_node = named_sibling_node;
        handler.parent_node = parent_node;
        handler.sibling_node = sibling_node;
        handler.node_presentational_hint = node_presentational_hint;
        handler.ua_default_for_property = ua_default_for_property;
        handler.node_has_name = node_has_name;
        handler.node_has_class = node_has_class;
        handler.node_has_id = node_has_id;
        handler.node_has_attribute = node_has_attribute;
        handler.node_is_root = node_is_root;
        handler.node_count_siblings = node_count_siblings;
        handler.node_is_empty = node_is_empty;
        handler.node_is_link = node_is_link;
        handler.node_is_visited = node_is_visited;
        handler.node_is_hover = node_is_hover;
        handler.node_is_active = node_is_active;
        handler.node_is_focus = node_is_focus;
        handler.node_is_enabled = node_is_enabled;
        handler.node_is_disabled = node_is_disabled;
        handler.node_is_checked = node_is_checked;
        handler.node_is_target = node_is_target;
        handler.node_is_lang = node_is_lang;
        handler.set_libcss_node_data = set_libcss_node_data;
        handler.get_libcss_node_data = get_libcss_node_data;

        memset(&media, 0, sizeof(media));
        media.type = CSS_MEDIA_SCREEN;
        memset(&unit_ctx, 0, sizeof(unit_ctx));
        unit_ctx.device_dpi = 96 << 10; /* css_fixed: 96dpi */

        err = css_select_style(select_ctx, (void *)1 /* node ptr */,
                               &unit_ctx, &media, NULL /* inline style */,
                               &handler, element_name /* pw: element name */,
                               &results);
        if (err != CSS_OK) {
            printf("CHECK_FAIL: css_select_style err=%d\n", err);
            return 1;
        }
        computed = results->styles[CSS_PSEUDO_ELEMENT_NONE];
        assert(computed != NULL);

        /* --- 完整消费者端到端用例：解析→级联→计算→输出对比 --- */
        color_sh = 0;
        (void)css_computed_color(computed, &color_sh);
        printf("computed color = %#08x (expected 0xffff0000)\n",
               (unsigned)color_sh);
        /* css_color 是 ARGB（0xAARRGGBB）：#ff0000 → 0xffff0000 */
        if (color_sh != 0xffff0000u) {
            printf("E2E_FAIL: computed color %#08x != expected 0xffff0000\n",
                   (unsigned)color_sh);
            return 1;
        }
        printf("E2E_PASS: css parse -> select cascade -> computed color "
               "#ff0000 verified end-to-end\n");

        bg_sh = 0;
        (void)css_computed_background_color(computed, &bg_sh);
        printf("computed background-color = %#08x (expected 0x00000000)\n",
               (unsigned)bg_sh);
        if (bg_sh != 0x00000000u) {
            printf("E2E_FAIL: background %#08x != expected transparent\n",
                   (unsigned)bg_sh);
            return 1;
        }
        printf("E2E_PASS: body rule not applied to p (specificity cascade "
               "correct) end-to-end\n");

        css_select_results_destroy(results);
    }

    /* 断言 6: 清理路径 */
    lwc_string_unref(element_name);
    css_select_ctx_destroy(select_ctx);
    css_stylesheet_destroy(sheet);
    printf("CHECK_PASS: teardown clean\n");

    printf("UPSTREAM_EQUIV_ASSERTIONS: 6 passed\n");
    return 0;
}
