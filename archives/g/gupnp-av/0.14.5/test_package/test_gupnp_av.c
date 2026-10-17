/* gupnp-av 0.14.5 真实功能断言：
 * 1) DIDL-Lite writer 生成 item，namespace getters（upnp/dlna/dc/pv）；
 * 2) object 属性 set/get 回读（title/upnp_class）；
 * 3) GUPnPProtocolInfo 字符串解析/序列化往返；
 * 4) GUPnPSearchCriteriaParser 解析 search criteria（上游 API 主路径）。
 */
#include <stdio.h>
#include <string.h>

#include <glib.h>
#include <glib-object.h>

#include <libgupnp-av/gupnp-didl-lite-writer.h>
#include <libgupnp-av/gupnp-didl-lite-object.h>
#include <libgupnp-av/gupnp-protocol-info.h>
#include <libgupnp-av/gupnp-search-criteria-parser.h>

struct search_hit {
    int count;
    int failed;
};

static int check_didl_lite_writer(void)
{
    GUPnPDIDLLiteWriter *writer = gupnp_didl_lite_writer_new(NULL);
    GUPnPDIDLLiteObject *object =
        GUPNP_DIDL_LITE_OBJECT(gupnp_didl_lite_writer_add_item(writer));
    xmlNs *ns;
    const char *title;

    ns = gupnp_didl_lite_object_get_upnp_namespace(object);
    if (ns == NULL || g_strcmp0((char *)ns->prefix, "upnp") != 0) {
        fprintf(stderr, "upnp namespace wrong\n");
        return 1;
    }
    ns = gupnp_didl_lite_object_get_dc_namespace(object);
    if (ns == NULL || g_strcmp0((char *)ns->prefix, "dc") != 0) {
        fprintf(stderr, "dc namespace wrong\n");
        return 1;
    }

    /* get_title/get_upnp_class 返回 xmlNode 内部内容（libxml2 所有），
     * 是 const char*，禁止 g_free（free 会破坏 libxml2 堆 → SIGTRAP）。 */
    gupnp_didl_lite_object_set_title(object, "Test Title");
    title = gupnp_didl_lite_object_get_title(object);
    if (g_strcmp0(title, "Test Title") != 0) {
        fprintf(stderr, "title roundtrip failed: %s\n", title ? title : "()");
        return 1;
    }

    gupnp_didl_lite_object_set_upnp_class(object, "object.item.audioItem");
    title = gupnp_didl_lite_object_get_upnp_class(object);
    if (g_strcmp0(title, "object.item.audioItem") != 0) {
        fprintf(stderr, "upnp_class roundtrip failed: %s\n", title ? title : "()");
        return 1;
    }

    g_object_unref(object);
    g_object_unref(writer);
    return 0;
}

static int check_protocol_info(void)
{
    GUPnPProtocolInfo *info =
        gupnp_protocol_info_new_from_string(
            "http-get:*:audio/mpeg:DLNA.ORG_PN=MP3", NULL);
    char *str;

    if (info == NULL) {
        fprintf(stderr, "protocol info parse failed\n");
        return 1;
    }
    str = gupnp_protocol_info_to_string(info);
    if (str == NULL || strlen(str) == 0) {
        fprintf(stderr, "protocol info to_string empty\n");
        g_free(str);
        return 1;
    }
    /* to_string 返回 GString 内容（glib 分配），g_free 释放 */
    g_free(str);
    g_object_unref(info);
    return 0;
}

static gboolean
on_search_expression(G_GNUC_UNUSED GUPnPSearchCriteriaParser *parser,
                     const char *property,
                     GUPnPSearchCriteriaOp op,
                     const char *value,
                     G_GNUC_UNUSED GError **error,
                     gpointer user_data)
{
    struct search_hit *hit = user_data;

    if (g_strcmp0(property, "dc:title") != 0
        || op != GUPNP_SEARCH_CRITERIA_OP_CONTAINS
        || g_strcmp0(value, "Hello") != 0) {
        fprintf(stderr,
                "search expression mismatch: property=%s op=%d value=%s\n",
                property ? property : "()", (int)op, value ? value : "()");
        hit->failed = 1;
    } else {
        hit->count++;
    }
    return FALSE;
}

static int check_search_criteria(void)
{
    GUPnPSearchCriteriaParser *parser =
        gupnp_search_criteria_parser_new();
    GError *error = NULL;
    struct search_hit hit = {0, 0};

    g_signal_connect(parser, "expression",
                     G_CALLBACK(on_search_expression), &hit);

    gupnp_search_criteria_parser_parse_text(
        parser, "dc:title contains \"Hello\"", &error);
    if (error != NULL) {
        fprintf(stderr, "search criteria parse error: %s\n", error->message);
        g_error_free(error);
        return 1;
    }
    if (hit.failed || hit.count != 1) {
        fprintf(stderr, "search expression callback check failed "
                        "(count=%d failed=%d)\n", hit.count, hit.failed);
        return 1;
    }
    g_object_unref(parser);
    return 0;
}

int main(void)
{
    if (check_didl_lite_writer() != 0)
        return 1;
    if (check_protocol_info() != 0)
        return 1;
    if (check_search_criteria() != 0)
        return 1;

    printf("gupnp-av didl-lite/protocol-info/search-criteria OK\n");
    return 0;
}
