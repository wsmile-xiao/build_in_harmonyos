/* test_package consumer test for libgepub 0.7.3 (headless core).
 *
 * Exercises real library API in 6 groups / 16 assertions, no display needed:
 *   A. GepubTextChunk create + type/text roundtrip (3 checks)
 *   B. GepubTextChunk header/bold/italic variants (3 checks)
 *   C. GepubArchive file enumeration + rootfile (2 checks)
 *   D. GepubDoc open + metadata + chapters (4 checks)
 *   E. GepubDoc text extraction contains the fixture paragraph (2 checks)
 *   F. GepubDoc TOC + spine/chapter mapping (2 checks)
 *
 * Usage: ./test_libgepub <book.epub>   (book.epub from make_book.py)
 * Prints TAP-style "ok N name" lines, "# diag:" diagnostic lines with the
 * actual values seen on the device, a SUMMARY line plus a FAILED_NAMES line
 * (so even a truncated log tail identifies the culprit), and exits 0 only
 * when every check passes (any failure -> exit 1, so conan test fails
 * loudly instead of passing silently).
 */
#include <gepub.h>

#include <stddef.h>
#include <stdio.h>
#include <string.h>

static int total_checks = 0;
static int failed_checks = 0;
static int total_groups = 0;
static int failed_groups = 0;
static int group_failed = 0;
static char failed_names[2048] = "";
static size_t failed_names_len = 0;

#define GROUP_BEGIN(name) \
    do { total_groups++; group_failed = 0; printf("# group: %s\n", name); fflush(stdout); } while (0)
#define GROUP_END() \
    do { if (group_failed) failed_groups++; \
         printf("# group result: %s\n", group_failed ? "FAIL" : "PASS"); fflush(stdout); } while (0)
#define CHECK(cond, name) \
    do { total_checks++; \
         if (cond) { printf("ok %d %s\n", total_checks, name); } \
         else { failed_checks++; group_failed = 1; \
                printf("not ok %d %s\n", total_checks, name); \
                if (failed_names_len + strlen(name) + 2 < sizeof(failed_names)) { \
                    if (failed_names_len > 0) { \
                        strcat(failed_names, ","); \
                        failed_names_len++; \
                    } \
                    strcat(failed_names, name); \
                    failed_names_len += strlen(name); \
                } } \
         fflush(stdout); } while (0)
#define DIAG(...) \
    do { printf("# diag: "); printf(__VA_ARGS__); printf("\n"); fflush(stdout); } while (0)

static void print_trunc(const char *tag, const char *s)
{
    if (s == NULL) {
        DIAG("%s=(null)", tag);
        return;
    }
    /* Truncate long blobs so the log tail stays readable. */
    if (strlen(s) > 300)
        DIAG("%s len=%lu first300=[%.300s]", tag, (unsigned long)strlen(s), s);
    else
        DIAG("%s len=%lu val=[%s]", tag, (unsigned long)strlen(s), s);
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <book.epub>\n", argv[0]);
        return 2;
    }
    const char *epub = argv[1];
    DIAG("fixture=[%s]", epub);

    /* A. text chunk basics */
    GROUP_BEGIN("text-chunk");
    {
        GepubTextChunk *c = gepub_text_chunk_new(GEPUBTextNormal, "hello");
        CHECK(c != NULL, "chunk-new-nonnull");
        CHECK(c != NULL && gepub_text_chunk_type(c) == GEPUBTextNormal, "chunk-type-roundtrip");
        CHECK(c != NULL && gepub_text_chunk_text(c) != NULL &&
              strcmp(gepub_text_chunk_text(c), "hello") == 0 &&
              gepub_text_chunk_type_str(c) != NULL, "chunk-text-roundtrip");
        if (c != NULL)
            g_object_unref(c);
    }
    GROUP_END();

    /* B. text chunk variants */
    GROUP_BEGIN("text-chunk-variants");
    {
        GepubTextChunk *h = gepub_text_chunk_new(GEPUBTextHeader, "Chapter 1");
        GepubTextChunk *b = gepub_text_chunk_new(GEPUBTextBold, "bold");
        GepubTextChunk *i = gepub_text_chunk_new(GEPUBTextItalic, "italic");
        CHECK(h != NULL && gepub_text_chunk_type(h) == GEPUBTextHeader &&
              strcmp(gepub_text_chunk_text(h), "Chapter 1") == 0, "chunk-header");
        CHECK(b != NULL && gepub_text_chunk_type(b) == GEPUBTextBold &&
              strcmp(gepub_text_chunk_text(b), "bold") == 0, "chunk-bold");
        CHECK(i != NULL && gepub_text_chunk_type(i) == GEPUBTextItalic &&
              strcmp(gepub_text_chunk_text(i), "italic") == 0 &&
              gepub_text_chunk_type_str(i) != NULL, "chunk-italic");
        if (h != NULL)
            g_object_unref(h);
        if (b != NULL)
            g_object_unref(b);
        if (i != NULL)
            g_object_unref(i);
    }
    GROUP_END();

    /* C. archive enumeration */
    GROUP_BEGIN("archive");
    {
        static const char *expected[] = {
            "mimetype",
            "META-INF/container.xml",
            "OEBPS/content.opf",
            "OEBPS/ch1.xhtml",
            "OEBPS/toc.ncx"
        };
        GepubArchive *a = gepub_archive_new(epub);
        int found = 0;
        int nlisted = 0;
        GList *files = NULL;
        DIAG("archive-new=%s", (a != NULL) ? "nonnull" : "NULL");
        if (a != NULL)
            files = gepub_archive_list_files(a);
        for (GList *l = files; l != NULL; l = l->next) {
            nlisted++;
            DIAG("archive-entry[%d]=[%s]", nlisted, (const char *)l->data);
        }
        DIAG("archive-nlisted=%d", nlisted);
        if (files != NULL) {
            size_t k;
            for (k = 0; k < sizeof(expected) / sizeof(expected[0]); k++) {
                GList *l;
                for (l = files; l != NULL; l = l->next) {
                    if (strcmp((const char *)l->data, expected[k]) == 0)
                        break;
                }
                if (l != NULL)
                    found++;
                else
                    DIAG("archive-missing=[%s]", expected[k]);
            }
        }
        DIAG("archive-found=%d expected=5", found);
        CHECK(found == 5, "archive-lists-all-5-entries");
        {
            char *root = (a != NULL) ? gepub_archive_get_root_file(a) : NULL;
            print_trunc("archive-rootfile", root);
            /* "content.opf" is 11 chars; use a suffix match instead of a
             * hand-rolled offset (a previous revision used -12 and could
             * never match "OEBPS/content.opf"). */
            int ok = root != NULL && g_str_has_suffix(root, "content.opf");
            CHECK(ok, "archive-rootfile-is-content.opf");
            g_free(root);
        }
        if (files != NULL) {
            g_list_foreach(files, (GFunc)g_free, NULL);
            g_list_free(files);
        }
        if (a != NULL)
            g_object_unref(a);
    }
    GROUP_END();

    /* D. document metadata */
    GROUP_BEGIN("doc-metadata");
    {
        GepubDoc *doc = gepub_doc_new(epub, NULL);
        DIAG("doc-new=%s", (doc != NULL) ? "nonnull" : "NULL");
        CHECK(doc != NULL, "doc-open");
        {
            char *title = (doc != NULL) ? gepub_doc_get_metadata(doc, GEPUB_META_TITLE) : NULL;
            print_trunc("doc-title", title);
            CHECK(title != NULL && strcmp(title, "HMBS Test Book") == 0, "doc-title");
            g_free(title);
        }
        {
            char *author = (doc != NULL) ? gepub_doc_get_metadata(doc, GEPUB_META_AUTHOR) : NULL;
            print_trunc("doc-author", author);
            CHECK(author != NULL && strcmp(author, "HMBS Team") == 0, "doc-author");
            g_free(author);
        }
        {
            int n = (doc != NULL) ? gepub_doc_get_n_chapters(doc) : -1;
            DIAG("doc-n-chapters=%d", n);
            CHECK(doc != NULL && n >= 1, "doc-chapters-ge-1");
        }
        if (doc != NULL)
            g_object_unref(doc);
    }
    GROUP_END();

    /* E. text extraction (public getters only; direct struct field reads
     * replaced so odd platform struct layouts cannot skew the result). */
    GROUP_BEGIN("doc-text");
    {
        GepubDoc *doc = gepub_doc_new(epub, NULL);
        GList *chunks = (doc != NULL) ? gepub_doc_get_text(doc) : NULL;
        int nchunks = (int)g_list_length(chunks);
        DIAG("doc-text-nchunks=%d", nchunks);
        CHECK(chunks != NULL, "doc-text-nonempty");
        {
            GString *all = g_string_new(NULL);
            int idx = 0;
            GList *l;
            for (l = chunks; l != NULL; l = l->next) {
                idx++;
                if (!GEPUB_IS_TEXT_CHUNK(l->data)) {
                    DIAG("doc-text-chunk[%d]=<non-text-chunk>", idx);
                    continue;
                }
                {
                    GepubTextChunk *chunk = GEPUB_TEXT_CHUNK(l->data);
                    const char *t = gepub_text_chunk_text(chunk);
                    DIAG("doc-text-chunk[%d] type=%d text=[%.120s]",
                         idx, (int)gepub_text_chunk_type(chunk),
                         (t != NULL) ? t : "<null>");
                    if (t != NULL)
                        g_string_append(all, t);
                }
            }
            print_trunc("doc-text-concat", all->str);
            CHECK(strstr(all->str, "Hello OHOS") != NULL, "doc-text-has-fixture-paragraph");
            g_string_free(all, TRUE);
        }
        if (doc != NULL)
            g_object_unref(doc);
    }
    GROUP_END();

    /* F. TOC and spine mapping */
    GROUP_BEGIN("doc-toc");
    {
        GepubDoc *doc = gepub_doc_new(epub, NULL);
        GList *toc = (doc != NULL) ? gepub_doc_get_toc(doc) : NULL;
        int ntoc = (int)g_list_length(toc);
        DIAG("doc-toc-length=%d", ntoc);
        CHECK(toc != NULL && toc->data != NULL, "doc-toc-nonempty");
        {
            int ok = 0;
            int map = -999;
            if (toc != NULL && toc->data != NULL) {
                GepubNavPoint *pt = (GepubNavPoint *)toc->data;
                print_trunc("doc-toc-first-label", pt->label);
                print_trunc("doc-toc-first-content", pt->content);
                DIAG("doc-toc-first-playorder=%llu",
                     (unsigned long long)pt->playorder);
                if (pt->content != NULL && doc != NULL)
                    map = gepub_doc_resource_uri_to_chapter(doc, pt->content);
                DIAG("doc-toc-uri-to-chapter=%d", map);
                ok = pt->label != NULL && strstr(pt->label, "Chapter") != NULL &&
                     doc != NULL && map >= 0;
            }
            CHECK(ok, "doc-toc-first-label-and-chapter-map");
        }
        if (doc != NULL)
            g_object_unref(doc);
    }
    GROUP_END();

    printf("SUMMARY groups=%d failed_groups=%d checks=%d failed_checks=%d\n",
           total_groups, failed_groups, total_checks, failed_checks);
    printf("FAILED_NAMES=[%s]\n", failed_names);
    printf("LIBGEPUB_TEST_SUMMARY discovered=%d passed=%d failed=%d\n",
           total_groups, total_groups - failed_groups, failed_groups);
    fflush(stdout);
    return (failed_checks == 0 && total_checks == 16 && total_groups == 6) ? 0 : 1;
}
