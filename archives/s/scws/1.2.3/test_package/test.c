/*
 * test_package/test.c — SCWS 1.2.3 consumer test (C API).
 *
 * Independent check items (counting convention: one [CHECK] line = 1 item):
 *   T1  version macro from the installed headers (SCWS_VERSION)
 *   T2  build a real xdb dictionary through the public xdb_* write API
 *       (xdb_create/xdb_nput/xdb_optimize/xdb_close; write path takes an
 *       exclusive file lock via _xdb_flock, exactly like scws-gen-dict)
 *   T3  segment "我爱北京天安门" with the xdb dict in mmap-backed
 *       SCWS_XDICT_XDB mode (read path used by production deployments)
 *   T4  segment the same sentence from a plain-text dict in
 *       SCWS_XDICT_TXT|SCWS_XDICT_MEM mode (in-memory; the non-MEM txt
 *       mode stages a temp xdb under /tmp which is read-only on OHOS,
 *       so consumers must use MEM mode there)
 *   T5  reload the engine with the packaged ruleset (etc/rules.utf8.ini)
 *       plus the xdb dict and re-segment
 *   T6  [OHOS only] mmap() the xdb file directly and verify the XDB
 *       header tag — the exact mechanism libscws/xdb.c uses under
 *       HAVE_MMAP on HarmonyOS
 *   T7  [OHOS only] flock(LOCK_EX|LOCK_NB)/LOCK_UN on the xdb file —
 *       the lock primitive libscws/lock.c relies on for dictionary
 *       creation on HarmonyOS
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <scws/scws.h>
#include <scws/xdict.h>
#include <scws/xdb.h>
#include <unistd.h>

#if defined(__OHOS__)
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/file.h>
#include <sys/stat.h>
#endif

static int g_fail = 0;

#define CHECK(cond, name) do {                                  \
    if (cond) { printf("[PASS] %s\n", name); }                  \
    else { printf("[FAIL] %s\n", name); g_fail++; }             \
} while (0)

static int u8len(unsigned char c)
{
    if (c < 0x80) return 1;
    if (c >= 0xf0) return 4;
    if (c >= 0xe0) return 3;
    return 2;
}

/* Replicates cli/gen_dict.c record layout: a FULL entry for the word
 * itself plus PART entries for every prefix of >= 2 chars (prefixes of
 * 1 char are never consulted by the segmenter extension loop). */
static void xdb_add_word(xdb_t x, const char *word)
{
    word_st w;
    size_t len = strlen(word), i;

    memset(&w, 0, sizeof(w));
    w.tf = w.idf = 1.0f;
    w.flag = SCWS_WORD_FULL;
    w.attr[0] = '@';
    xdb_nput(x, &w, sizeof(w), (void *) word, (int) len);

    i = u8len((unsigned char) word[0]);
    while (i < len)
    {
        i += u8len((unsigned char) word[i]);
        if (i >= len)
            break;
        memset(&w, 0, sizeof(w));
        w.flag = SCWS_WORD_PART;
        xdb_nput(x, &w, sizeof(w), (void *) word, (int) i);
    }
}

/* Segment `text` and return "tok1/tok2/.../" in a static buffer. */
static const char *segment_text(const char *dict_path, int mode,
                                const char *rule_path, const char *text)
{
    static char buf[1024];
    scws_t s;
    scws_res_t res, cur;
    size_t pos = 0;

    buf[0] = '\0';
    s = scws_new();
    if (s == NULL)
        return NULL;
    scws_set_charset(s, "utf8");
    if (rule_path != NULL)
        scws_set_rule(s, rule_path);
    if (scws_set_dict(s, dict_path, mode) != 0)
    {
        scws_free(s);
        return NULL;
    }
    scws_send_text(s, text, (int) strlen(text));
    /* Tokens arrive in batches: iterate scws_get_result() until NULL. */
    while ((res = scws_get_result(s)) != NULL)
    {
        for (cur = res; cur != NULL; cur = cur->next)
        {
            int n = snprintf(buf + pos, sizeof(buf) - pos, "%.*s/",
                             (int) cur->len, text + cur->off);
            if (n < 0 || (size_t) n >= sizeof(buf) - pos)
            {
                pos = sizeof(buf) - 1;
                break;
            }
            pos += (size_t) n;
        }
        scws_free_result(res);
        if (pos >= sizeof(buf) - 1)
            break;
    }
    scws_free(s);
    return buf;
}

int main(int argc, char **argv)
{
    const char *workdir = (argc > 1) ? argv[1] : ".";
    const char *rules = (argc > 2) ? argv[2] : NULL;
    char xdb_path[1024], txt_path[1024];
    static const char *words[] = { "我", "爱", "北京", "天安门", "中国" };
    const char *sentence = "我爱北京天安门";
    const char *expect = "我/爱/北京/天安门/";
    const char *got;
    xdb_t x;
    FILE *fp;
    size_t i;

    printf("=== scws 1.2.3 consumer test ===\n");

    /* T1: version macro from installed headers */
    CHECK(strcmp(SCWS_VERSION, "1.2.3") == 0, "T1 SCWS_VERSION == 1.2.3");

    snprintf(xdb_path, sizeof(xdb_path), "%s/test_dict.xdb", workdir);
    snprintf(txt_path, sizeof(txt_path), "%s/test_dict.txt", workdir);

    /* T2: build a real xdb dictionary via the public write API */
    x = xdb_create(xdb_path, 0, SCWS_XDICT_PRIME);
    if (x != NULL)
    {
        for (i = 0; i < sizeof(words) / sizeof(words[0]); i++)
            xdb_add_word(x, words[i]);
        xdb_optimize(x);
        xdb_close(x);
    }
    x = xdb_open(xdb_path, 0);
    CHECK(x != NULL, "T2 xdb_create/xdb_nput/xdb_optimize + reopen");
    if (x != NULL)
        xdb_close(x);

    /* T3: mmap-backed xdb dict segmentation */
    got = segment_text(xdb_path, SCWS_XDICT_XDB, NULL, sentence);
    CHECK(got != NULL && strcmp(got, expect) == 0,
          "T3 xdb dict segmentation 我爱北京天安门");
    if (got != NULL)
        printf("       got: %s\n", got);

    /* T4: plain-text dict in MEM mode (no /tmp staging file) */
    fp = fopen(txt_path, "w");
    if (fp != NULL)
    {
        for (i = 0; i < sizeof(words) / sizeof(words[0]); i++)
            fprintf(fp, "%s\t1.0\t1.0\t@\n", words[i]);
        fclose(fp);
    }
    got = segment_text(txt_path, SCWS_XDICT_TXT | SCWS_XDICT_MEM, NULL,
                       sentence);
    CHECK(got != NULL && strcmp(got, expect) == 0,
          "T4 txt dict (MEM mode) segmentation");
    if (got != NULL)
        printf("       got: %s\n", got);

    /* T5: packaged ruleset + xdb dict */
    if (rules != NULL)
    {
        got = segment_text(xdb_path, SCWS_XDICT_XDB, rules, sentence);
        CHECK(got != NULL && strcmp(got, expect) == 0,
              "T5 packaged rules.utf8.ini + xdb segmentation");
        if (got != NULL)
            printf("       got: %s\n", got);
    }

#if defined(__OHOS__)
    /* T6/T7: HarmonyOS platform primitives that libscws relies on */
    {
        int fd = open(xdb_path, O_RDONLY);
        struct stat st;
        void *m = MAP_FAILED;

        if (fd >= 0 && fstat(fd, &st) == 0 && st.st_size > 0)
            m = mmap(NULL, (size_t) st.st_size, PROT_READ, MAP_SHARED, fd, 0);
        CHECK(m != MAP_FAILED && memcmp(m, XDB_TAGNAME, 3) == 0,
              "T6 OHOS mmap() maps xdb and exposes XDB header tag");
        if (m != MAP_FAILED)
            munmap(m, (size_t) st.st_size);
        CHECK(fd >= 0 && flock(fd, LOCK_EX | LOCK_NB) == 0
              && flock(fd, LOCK_UN) == 0,
              "T7 OHOS flock() LOCK_EX/LOCK_UN on xdb file");
        if (fd >= 0)
            close(fd);
    }
#else
    printf("[SKIP] T6/T7 OHOS-specific mmap/flock checks (not OHOS)\n");
#endif

    unlink(xdb_path);
    unlink(txt_path);

    if (g_fail != 0)
    {
        printf("=== %d check(s) FAILED ===\n", g_fail);
        return 1;
    }
    printf("=== all checks PASSED ===\n");
    return 0;
}
