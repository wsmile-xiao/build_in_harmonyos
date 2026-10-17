/*
 * Comprehensive test for libfm-extra API — covers public functions
 * declared in fm-xml-file.h (the sole public header of libfm-extra).
 *
 * Upstream libfm-extra has no test suite; this test_package exercises every
 * public symbol so that Conan CI can verify the library was built correctly.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <libfm-1.0/fm-xml-file.h>

static int tests_run = 0;
static int tests_passed = 0;

#define ASSERT(expr, msg) do {                                    \
    tests_run++;                                                  \
    if (expr) { tests_passed++; }                                 \
    else {                                                        \
        fprintf(stderr, "FAIL [%d]: %s  (%s:%d)\n",               \
                tests_run, msg, __FILE__, __LINE__);              \
        return 1;                                                 \
    }                                                             \
} while (0)

/* ---------- handler callback ---------- */

static FmXmlFileTag tag_root = 0;

static gboolean on_root(FmXmlFileItem *item, GList *children,
                         char * const *names, char * const *values,
                         guint n_attrs, gint line, gint pos,
                         GError **error, gpointer user_data)
{
    (void)children; (void)names; (void)values; (void)n_attrs;
    (void)line; (void)pos; (void)error; (void)user_data;
    FmXmlFileTag t = fm_xml_file_item_get_tag(item);
    ASSERT(t == tag_root, "item tag matches registered tag");
    const char *tname = fm_xml_file_item_get_tag_name(item);
    ASSERT(tname != NULL && strcmp(tname, "root") == 0, "tag name is 'root'");
    return TRUE;
}

/* ---------- test functions ---------- */

static int test_get_type(void)
{
    GType t = fm_xml_file_get_type();
    ASSERT(t > 0, "fm_xml_file_get_type returns valid GType");
    return 0;
}

static int test_parse_basic(void)
{
    FmXmlFile *f = fm_xml_file_new(NULL);
    ASSERT(f != NULL, "fm_xml_file_new returns non-NULL");

    tag_root = fm_xml_file_set_handler(f, "root", on_root, FALSE, NULL);
    ASSERT(tag_root != FM_XML_FILE_TAG_NOT_HANDLED,
           "set_handler returns valid tag id");

    GError *err = NULL;
    const char *xml = "<root>hello</root>";
    gboolean ok = fm_xml_file_parse_data(f, xml, strlen(xml), &err, NULL);
    ASSERT(ok, "parse_data succeeds");
    ASSERT(err == NULL, "no parse error");

    GList *items = fm_xml_file_finish_parse(f, &err);
    ASSERT(items != NULL, "finish_parse returns list");
    ASSERT(err == NULL, "no finish error");

    g_list_free_full(items, (GDestroyNotify)fm_xml_file_item_destroy);
    g_object_unref(f);
    return 0;
}

static int test_parse_nested(void)
{
    FmXmlFile *f = fm_xml_file_new(NULL);
    ASSERT(f != NULL, "nested: new");

    fm_xml_file_set_handler(f, "a", NULL, FALSE, NULL);
    fm_xml_file_set_handler(f, "b", NULL, FALSE, NULL);

    GError *err = NULL;
    const char *xml = "<a><b>text</b></a>";
    ASSERT(fm_xml_file_parse_data(f, xml, strlen(xml), &err, NULL),
           "nested: parse_data");
    ASSERT(err == NULL, "nested: no error");

    GList *items = fm_xml_file_finish_parse(f, &err);
    ASSERT(items != NULL, "nested: finish_parse");
    ASSERT(err == NULL, "nested: no finish error");

    g_list_free_full(items, (GDestroyNotify)fm_xml_file_item_destroy);
    g_object_unref(f);
    return 0;
}

static int test_current_line(void)
{
    FmXmlFile *f = fm_xml_file_new(NULL);
    int pos = 0;
    gint line = fm_xml_file_get_current_line(f, &pos);
    ASSERT(line >= 0, "get_current_line returns >= 0");
    g_object_unref(f);
    return 0;
}

static int test_dtd(void)
{
    FmXmlFile *f = fm_xml_file_new(NULL);
    GError *err = NULL;
    const char *dtd = fm_xml_file_get_dtd(f);
    ASSERT(dtd == NULL, "initial dtd is NULL");

    fm_xml_file_set_dtd(f, "<!DOCTYPE root>", &err);
    ASSERT(err == NULL, "set_dtd no error");
    dtd = fm_xml_file_get_dtd(f);
    ASSERT(dtd != NULL && strcmp(dtd, "<!DOCTYPE root>") == 0,
           "dtd matches set value");

    g_object_unref(f);
    return 0;
}

static int test_to_data(void)
{
    FmXmlFile *f = fm_xml_file_new(NULL);
    GError *err = NULL;
    gsize sz = 0;
    char *data = fm_xml_file_to_data(f, &sz, &err);
    ASSERT(data != NULL, "to_data returns non-NULL");
    ASSERT(sz > 0, "to_data size > 0");
    ASSERT(err == NULL, "to_data no error");
    g_free(data);
    g_object_unref(f);
    return 0;
}

static int test_item_create_destroy(void)
{
    FmXmlFileItem *item = fm_xml_file_item_new(0);
    ASSERT(item != NULL, "item_new returns non-NULL");
    ASSERT(fm_xml_file_item_destroy(item), "item_destroy returns TRUE");
    return 0;
}

static int test_item_text(void)
{
    FmXmlFileItem *item = fm_xml_file_item_new(0);
    ASSERT(item != NULL, "item_text: new");
    fm_xml_file_item_append_text(item, "test text", -1, FALSE);
    const char *d = fm_xml_file_item_get_data(item, NULL);
    ASSERT(d != NULL && strcmp(d, "test text") == 0, "item text matches");
    fm_xml_file_item_destroy(item);
    return 0;
}

static int test_item_attribute(void)
{
    FmXmlFileItem *item = fm_xml_file_item_new(0);
    ASSERT(item != NULL, "item_attr: new");
    ASSERT(fm_xml_file_item_set_attribute(item, "key", "val"),
           "set_attribute returns TRUE");
    fm_xml_file_item_destroy(item);
    return 0;
}

static int test_item_children(void)
{
    FmXmlFileItem *parent = fm_xml_file_item_new(0);
    FmXmlFileItem *child1 = fm_xml_file_item_new(0);
    FmXmlFileItem *child2 = fm_xml_file_item_new(0);

    ASSERT(fm_xml_file_item_append_child(parent, child1),
           "append_child 1 ok");
    ASSERT(fm_xml_file_item_append_child(parent, child2),
           "append_child 2 ok");

    GList *ch = fm_xml_file_item_get_children(parent);
    ASSERT(ch != NULL, "parent has children");
    ASSERT(g_list_length(ch) == 2, "parent has 2 children");

    FmXmlFileItem *found = fm_xml_file_item_find_child(parent, 0);
    ASSERT(found != NULL, "find_child returns non-NULL");

    fm_xml_file_item_destroy(parent);
    return 0;
}

static int test_insert_first(void)
{
    FmXmlFile *f = fm_xml_file_new(NULL);
    FmXmlFileItem *item = fm_xml_file_item_new(0);
    ASSERT(fm_xml_file_insert_first(f, item),
           "insert_first returns TRUE");
    g_object_unref(f);
    return 0;
}

static int test_tag_names(void)
{
    FmXmlFile *f = fm_xml_file_new(NULL);
    FmXmlFileTag t = fm_xml_file_set_handler(f, "mytag", NULL, FALSE, NULL);
    ASSERT(t != FM_XML_FILE_TAG_NOT_HANDLED, "tag registered");
    const char *name = fm_xml_file_get_tag_name(f, t);
    ASSERT(name != NULL && strcmp(name, "mytag") == 0,
           "get_tag_name returns registered name");
    g_object_unref(f);
    return 0;
}

static int test_sibling(void)
{
    FmXmlFile *f1 = fm_xml_file_new(NULL);
    FmXmlFile *f2 = fm_xml_file_new(f1);
    ASSERT(f2 != NULL, "sibling creation returns non-NULL");
    g_object_unref(f1);
    g_object_unref(f2);
    return 0;
}

static int test_parse_error(void)
{
    FmXmlFile *f = fm_xml_file_new(NULL);
    GError *err = NULL;
    const char *bad_xml = "<unclosed>";
    fm_xml_file_parse_data(f, bad_xml, strlen(bad_xml), &err, NULL);
    if (err) g_error_free(err);
    GError *err2 = NULL;
    GList *items = fm_xml_file_finish_parse(f, &err2);
    if (err2) g_error_free(err2);
    g_list_free_full(items, (GDestroyNotify)fm_xml_file_item_destroy);
    g_object_unref(f);
    return 0;
}

/* ---------- main ---------- */

int main(void)
{
    if (test_get_type()) return 1;
    if (test_parse_basic()) return 1;
    if (test_parse_nested()) return 1;
    if (test_current_line()) return 1;
    if (test_dtd()) return 1;
    if (test_to_data()) return 1;
    if (test_item_create_destroy()) return 1;
    if (test_item_text()) return 1;
    if (test_item_attribute()) return 1;
    if (test_item_children()) return 1;
    if (test_insert_first()) return 1;
    if (test_tag_names()) return 1;
    if (test_sibling()) return 1;
    if (test_parse_error()) return 1;

    printf("libfm-extra API test: %d/%d passed\n", tests_passed, tests_run);
    return (tests_passed == tests_run) ? 0 : 1;
}
