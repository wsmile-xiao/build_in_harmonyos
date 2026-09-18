/******************************************************************************
 * test.c — qlibc 2.5.1 Conan test_package consumer test (HarmonyOS/OHOS)
 *
 * Real consumer verification: links the packaged libqlibc, exercises
 * containers (qvector/qlist/qhasharr), string utils and MD5, and returns
 * non-zero on any failure (R34: substantive API usage, not a print-only shell).
 *****************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include <qlibc/qlibc.h>
#include <qlibc/containers/qvector.h>
#include <qlibc/containers/qlist.h>
#include <qlibc/containers/qhasharr.h>
#include <qlibc/utilities/qstring.h>
#include <qlibc/utilities/qhash.h>

static int g_failures = 0;

#define CHECK(cond, msg)                        \
    do {                                        \
        if (!(cond)) {                          \
            g_failures++;                       \
            fprintf(stderr, "FAIL: %s\n", msg); \
        }                                       \
    } while (0)

int main(void)
{
    /* qvector: growable int vector */
    qvector_t *vec = qvector(4, sizeof(int), QVECTOR_RESIZE_DOUBLE);
    CHECK(vec != NULL, "qvector()");
    if (vec) {
        int i, v;
        for (i = 0; i < 16; i++) {
            int d = i * i;
            CHECK(qvector_addlast(vec, &d), "qvector_addlast");
        }
        CHECK(qvector_size(vec) == 16, "qvector_size");
        v = *(int *)qvector_getat(vec, 15, false);
        CHECK(v == 225, "qvector_getat(15)");
        qvector_free(vec);
    }

    /* qlist: string linked list */
    qlist_t *list = qlist(0);
    CHECK(list != NULL, "qlist()");
    if (list) {
        CHECK(qlist_addlast(list, "alpha", 6), "qlist_addlast");
        CHECK(qlist_addlast(list, "beta", 5), "qlist_addlast2");
        size_t n = 0;
        char *s = qlist_getat(list, 1, &n, true);
        CHECK(s && strcmp(s, "beta") == 0, "qlist_getat(1)");
        free(s);
        qlist_free(list);
    }

    /* qhasharr: static hash table */
    size_t memsize = qhasharr_calculate_memsize(8);
    void *mem = malloc(memsize);
    if (mem) {
        qhasharr_t *tbl = qhasharr(mem, memsize);
        CHECK(tbl != NULL, "qhasharr()");
        if (tbl) {
            CHECK(qhasharr_putstr(tbl, "k", "v"), "qhasharr_putstr");
            char *s = qhasharr_getstr(tbl, "k");
            CHECK(s && strcmp(s, "v") == 0, "qhasharr_getstr");
            free(s);
        }
        free(mem);
    }

    /* qstring: trim/case */
    char buf[64];
    snprintf(buf, sizeof(buf), "  hello qlibc  ");
    CHECK(strcmp(qstrtrim(buf), "hello qlibc") == 0, "qstrtrim");

    /* MD5 of "abc" must match RFC 1321 test vector */
    unsigned char md5[16];
    static const unsigned char expect[16] = {
        0x90, 0x01, 0x50, 0x98, 0x3c, 0xd2, 0x4f, 0xb0,
        0xd6, 0x96, 0x3f, 0x7d, 0x28, 0xe1, 0x7f, 0x72,
    };
    CHECK(qhashmd5("abc", 3, md5), "qhashmd5");
    CHECK(memcmp(md5, expect, 16) == 0, "qhashmd5 digest");

    if (g_failures == 0) {
        printf("qlibc test_package: ALL PASS\n");
        return 0;
    }
    fprintf(stderr, "qlibc test_package: %d FAILURES\n", g_failures);
    return 1;
}
