/* upstream_headless.c — headless port of upstream tests/test-gepub.c (libgepub 0.7.3).
 *
 * Upstream tests/test-gepub.c defines 7 TEST() cases run from main():
 *   test_open, test_read, test_root_file, test_doc_name,
 *   test_doc_resources, test_doc_spine, test_doc_toc
 * Each exercises only GepubArchive/GepubDoc (glib + libgepub, no display).
 * The surrounding harness needs gtk+-3.0 + webkit2gtk + display + gtk_main,
 * so `meson test` registers zero test() targets and -Dwidget=false skips
 * subdir(tests) entirely. This file vendors ONLY the 7 headless functions
 * (plus find_xhtml/pk helpers) verbatim, with PTEST mapped to plain printf,
 * and adds a PASS/FAIL assertion per case so a regression exits 1 instead
 * of printing silently (upstream only prints; see TEST() macro:
 *   #define TEST(f,arg...) PTEST("### TESTING " #f); f(arg); ...).
 *
 * Source audited: libgepub-0.7.3.tar.xz :: tests/test-gepub.c (GNOME,
 * https://download.gnome.org/sources/libgepub/0.7/libgepub-0.7.3.tar.xz).
 * GTK-only code (update_text/button_pressed/widget/window/gtk_main) is
 * intentionally excluded — it cannot run on OHOS (no webkit2gtk, no display).
 *
 * Usage: ./upstream_headless <book.epub>   (book.epub from make_book.py)
 * Prints "ok N name" per upstream case + "# diag:" values, SUMMARY line,
 * exits 0 iff 7/7 pass.
 */
#include <gepub.h>

#include <stdio.h>
#include <string.h>

#define PTEST(...) do { printf(__VA_ARGS__); fflush(stdout); } while (0)

static int total_checks = 0;
static int failed_checks = 0;
static char failed_names[1024] = "";
static size_t failed_names_len = 0;

#define CHECK(cond, name) \
    do { total_checks++; \
         if (cond) { printf("ok %d %s\n", total_checks, name); } \
         else { failed_checks++; \
                printf("not ok %d %s\n", total_checks, name); \
                if (failed_names_len + strlen(name) + 2 < sizeof(failed_names)) { \
                    if (failed_names_len > 0) { strcat(failed_names, ","); failed_names_len++; } \
                    strcat(failed_names, name); failed_names_len += strlen(name); \
                } } \
         fflush(stdout); } while (0)
#define DIAG(...) do { printf("# diag: "); printf(__VA_ARGS__); printf("\n"); fflush(stdout); } while (0)

/* ---- verbatim helpers from tests/test-gepub.c ---- */
static void
find_xhtml (gchar *key, GepubResource *value, gpointer data)
{
    gchar **d = (gchar **)data;
    (void)key;
    if (g_strcmp0 (value->mime, "application/xhtml+xml") == 0) {
        *d = value->uri;
    }
}

static void
pk (gchar *key, GepubResource *value, gpointer data)
{
    (void)data;
    PTEST ("%s: %s, %s\n", key, value->mime, value->uri);
}

/* Each upstream_test_* mirrors one upstream test_* function and returns 1 on pass. */
static int upstream_test_open(const char *path)
{
    GepubArchive *a;
    GList *list_files;
    gint size, i;
    PTEST("\n### TESTING test_open ###\n\n");
    a = gepub_archive_new(path);
    if (a == NULL) { DIAG("archive-new=NULL"); return 0; }
    list_files = gepub_archive_list_files(a);
    if (!list_files) { PTEST("ERROR: BAD epub file"); g_object_unref(a); return 0; }
    size = g_list_length(list_files);
    PTEST("%d\n", size);
    for (i = 0; i < size; i++) {
        PTEST("file: %s\n", (char *)g_list_nth_data(list_files, i));
    }
    DIAG("nlisted=%d", size);
    {
        static const char *expected[] = {
            "mimetype", "META-INF/container.xml", "OEBPS/content.opf",
            "OEBPS/ch1.xhtml", "OEBPS/toc.ncx"
        };
        int found = 0;
        size_t k;
        for (k = 0; k < sizeof(expected)/sizeof(expected[0]); k++) {
            GList *l;
            for (l = list_files; l; l = l->next)
                if (strcmp((const char *)l->data, expected[k]) == 0) break;
            if (l) found++;
            else DIAG("missing=[%s]", expected[k]);
        }
        g_list_foreach(list_files, (GFunc)g_free, NULL);
        g_list_free(list_files);
        g_object_unref(a);
        PTEST("\n\n");
        return (size == 5 && found == 5);
    }
}

static int upstream_test_read(const char *path)
{
    GepubArchive *a;
    const guchar *buffer;
    gchar *file = NULL;
    gsize bufsize = 0;
    GBytes *bytes = NULL;
    GepubDoc *doc;
    GHashTable *ht;
    int ok = 0;
    PTEST("\n### TESTING test_read ###\n\n");
    a = gepub_archive_new(path);
    doc = gepub_doc_new(path, NULL);
    if (a == NULL || doc == NULL) {
        DIAG("archive=%s doc=%s", a ? "ok" : "NULL", doc ? "ok" : "NULL");
        if (a) g_object_unref(a);
        if (doc) g_object_unref(G_OBJECT(doc));
        return 0;
    }
    ht = (GHashTable*)gepub_doc_get_resources(doc);
    g_hash_table_foreach(ht, (GHFunc)find_xhtml, &file);
    DIAG("xhtml-uri=[%s]", file ? file : "<null>");
    if (file != NULL) {
        bytes = gepub_archive_read_entry(a, file);
        if (bytes) {
            buffer = g_bytes_get_data(bytes, &bufsize);
            PTEST("doc:%s\n----\n%.*s\n-----\n", file, (int)bufsize, buffer);
            DIAG("read-bytes=%lu", (unsigned long)bufsize);
            ok = (bufsize > 0 && strstr((const char *)buffer, "Hello OHOS") != NULL);
            g_bytes_unref(bytes);
        } else {
            DIAG("read_entry returned NULL");
        }
    }
    g_object_unref(a);
    g_object_unref(G_OBJECT(doc));
    PTEST("\n\n");
    return ok;
}

static int upstream_test_root_file(const char *path)
{
    GepubArchive *a;
    gchar *root_file = NULL;
    int ok = 0;
    PTEST("\n### TESTING test_root_file ###\n\n");
    a = gepub_archive_new(path);
    if (a == NULL) return 0;
    root_file = gepub_archive_get_root_file(a);
    PTEST("root file: %s\n", root_file ? root_file : "<null>");
    DIAG("root=[%s]", root_file ? root_file : "<null>");
    ok = (root_file != NULL && g_str_has_suffix(root_file, "content.opf"));
    if (root_file) g_free(root_file);
    g_object_unref(a);
    PTEST("\n\n");
    return ok;
}

static int upstream_test_doc_name(const char *path)
{
    GepubDoc *doc = gepub_doc_new(path, NULL);
    gchar *title, *lang, *id, *author, *description, *cover, *cover_mime = NULL;
    int ok = 0;
    PTEST("\n### TESTING test_doc_name ###\n\n");
    if (doc == NULL) return 0;
    title = gepub_doc_get_metadata(doc, GEPUB_META_TITLE);
    lang = gepub_doc_get_metadata(doc, GEPUB_META_LANG);
    id = gepub_doc_get_metadata(doc, GEPUB_META_ID);
    author = gepub_doc_get_metadata(doc, GEPUB_META_AUTHOR);
    description = gepub_doc_get_metadata(doc, GEPUB_META_DESC);
    cover = gepub_doc_get_cover(doc);
    if (cover)
        cover_mime = gepub_doc_get_resource_mime_by_id(doc, cover);
    PTEST("title: %s\n", title ? title : "<null>");
    PTEST("author: %s\n", author ? author : "<null>");
    PTEST("id: %s\n", id ? id : "<null>");
    PTEST("lang: %s\n", lang ? lang : "<null>");
    PTEST("desc: %s\n", description ? description : "<null>");
    if (cover) PTEST("cover: %s\n", cover);
    if (cover_mime) PTEST("cover mime: %s\n", cover_mime);
    DIAG("title=[%s] author=[%s]", title ? title : "<null>", author ? author : "<null>");
    ok = (title && strcmp(title, "HMBS Test Book") == 0 &&
          author && strcmp(author, "HMBS Team") == 0);
    g_free(title); g_free(lang); g_free(id); g_free(author);
    g_free(description); g_free(cover); g_free(cover_mime);
    g_object_unref(G_OBJECT(doc));
    PTEST("\n\n");
    return ok;
}

static int upstream_test_doc_resources(const char *path)
{
    GepubDoc *doc;
    GHashTable *ht;
    GBytes *ncx = NULL;
    const guchar *data = NULL;
    gsize size = 0;
    int ok = 0;
    PTEST("\n### TESTING test_doc_resources ###\n\n");
    doc = gepub_doc_new(path, NULL);
    if (doc == NULL) return 0;
    ht = (GHashTable*)gepub_doc_get_resources(doc);
    if (ht == NULL) { g_object_unref(G_OBJECT(doc)); return 0; }
    DIAG("nresources=%u", g_hash_table_size(ht));
    g_hash_table_foreach(ht, (GHFunc)pk, NULL);
    ncx = gepub_doc_get_resource_by_id(doc, "ncx");
    if (ncx) {
        data = g_bytes_get_data(ncx, &size);
        PTEST("ncx:\n%.*s\n", (int)size, data);
        DIAG("ncx-bytes=%lu", (unsigned long)size);
        ok = (size > 0 && data != NULL && g_hash_table_size(ht) >= 2);
        g_bytes_unref(ncx);
    } else {
        DIAG("ncx resource missing");
    }
    g_object_unref(G_OBJECT(doc));
    PTEST("\n\n");
    return ok;
}

static int upstream_test_doc_spine(const char *path)
{
    GepubDoc *doc = gepub_doc_new(path, NULL);
    int id = 0, ok = 0;
    const char *cur;
    PTEST("\n### TESTING test_doc_spine ###\n\n");
    if (doc == NULL) return 0;
    do {
        cur = gepub_doc_get_current_id(doc);
        PTEST("%d: %s\n", id++, cur ? cur : "<null>");
        DIAG("spine[%d]=[%s]", id - 1, cur ? cur : "<null>");
    } while (gepub_doc_go_next(doc));
    DIAG("spine-count=%d", id);
    ok = (id >= 1);
    g_object_unref(G_OBJECT(doc));
    PTEST("\n\n");
    return ok;
}

static int upstream_test_doc_toc(const char *path)
{
    GepubDoc *doc = gepub_doc_new(path, NULL);
    GList *nav;
    int n = 0, ok = 0;
    PTEST("\n### TESTING test_doc_toc ###\n\n");
    if (doc == NULL) return 0;
    nav = gepub_doc_get_toc(doc);
    n = (int)g_list_length(nav);
    DIAG("toc-length=%d", n);
    while (nav && nav->data) {
        GepubNavPoint *point = (GepubNavPoint*)nav->data;
        /* Verbatim upstream 0.7.3 body (no depth field in 0.7.3's
         * struct _GepubNavPoint; depth was added only later on master). */
        PTEST("%02d: %s -> %s\n", (gint)point->playorder,
              point->label ? point->label : "<null>",
              point->content ? point->content : "<null>");
        PTEST(" -> Chapter: %d\n",
              point->content ? gepub_doc_resource_uri_to_chapter(doc, point->content) : -1);
        if (point->label && strstr(point->label, "Chapter") != NULL &&
            point->content != NULL &&
            gepub_doc_resource_uri_to_chapter(doc, point->content) >= 0)
            ok = 1;
        nav = nav->next;
    }
    DIAG("toc-ok=%d", ok);
    g_object_unref(G_OBJECT(doc));
    PTEST("\n\n");
    return (n >= 1 && ok);
}

int main(int argc, char **argv)
{
    const char *epub;
    if (argc < 2) { fprintf(stderr, "usage: %s <book.epub>\n", argv[0]); return 2; }
    epub = argv[1];
    DIAG("fixture=[%s]", epub);
    CHECK(upstream_test_open(epub), "test_open");
    CHECK(upstream_test_read(epub), "test_read");
    CHECK(upstream_test_root_file(epub), "test_root_file");
    CHECK(upstream_test_doc_name(epub), "test_doc_name");
    CHECK(upstream_test_doc_resources(epub), "test_doc_resources");
    CHECK(upstream_test_doc_spine(epub), "test_doc_spine");
    CHECK(upstream_test_doc_toc(epub), "test_doc_toc");
    printf("SUMMARY upstream_discovered=7 passed=%d failed=%d\n",
           total_checks - failed_checks, failed_checks);
    printf("FAILED_NAMES=[%s]\n", failed_names);
    printf("LIBGEPUB_UPSTREAM_SUMMARY discovered=7 passed=%d failed=%d\n",
           total_checks - failed_checks, failed_checks);
    fflush(stdout);
    return (failed_checks == 0 && total_checks == 7) ? 0 : 1;
}
