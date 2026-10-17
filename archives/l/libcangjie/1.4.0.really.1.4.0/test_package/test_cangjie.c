/* Consumer test for libcangjie: exercises the real public API.
 *
 * 6 checks, each prints one "CHECK-OK: <name>" line on success.
 * The conanfile counts those lines for the HMBS_TEST_PACKAGE_RESULT marker.
 * CANGJIE_DB env must point at the packaged share/libcangjie/cangjie.db;
 * cangjie_new() honours it (upstream behaviour for local testing).
 */
#include <stdio.h>
#include <string.h>

#include <cangjie/cangjie.h>
#include <cangjie/cangjiechar.h>
#include <cangjie/cangjiecharlist.h>
#include <cangjie/libcangjie.h>

int main(void) {
    /* 1: version API */
    const char *ver = libcangjie_version();
    if (ver == NULL || strlen(ver) == 0) {
        fprintf(stderr, "version empty\n");
        return 1;
    }
    if (strcmp(ver, LIBCANGJIE_VERSION) != 0) {
        fprintf(stderr, "version mismatch: %s vs %s\n", ver, LIBCANGJIE_VERSION);
        return 1;
    }
    printf("CHECK-OK: version %s\n", ver);

    /* 2: version compat check */
    if (libcangjie_check_version_gte(LIBCANGJIE_VERSION_MAJOR,
                                     LIBCANGJIE_VERSION_MINOR,
                                     LIBCANGJIE_VERSION_PATCH) != 1) {
        fprintf(stderr, "check_version_gte failed\n");
        return 1;
    }
    printf("CHECK-OK: check_version_gte\n");

    /* 3: char object lifecycle */
    {
        CangjieChar *c = NULL;
        int ret = cangjie_char_new(&c, "a", "b", "abc", 123);
        if (ret != CANGJIE_OK || c == NULL) {
            fprintf(stderr, "char_new failed: %d\n", ret);
            return 1;
        }
        if (strcmp(c->chchar, "a") != 0 || strcmp(c->code, "abc") != 0
            || c->frequency != 123) {
            fprintf(stderr, "char fields mismatch\n");
            cangjie_char_free(c);
            return 1;
        }
        cangjie_char_free(c);
    }
    printf("CHECK-OK: char_new_free\n");

    /* 4: char list append/prepend */
    {
        CangjieCharList *l = NULL;
        CangjieChar *c1 = NULL;
        CangjieChar *c2 = NULL;
        if (cangjie_char_new(&c1, "a", "a", "ddd", 1) != CANGJIE_OK
            || cangjie_char_list_append(&l, c1) != CANGJIE_OK || l->c != c1) {
            fprintf(stderr, "char_list_append failed\n");
            return 1;
        }
        if (cangjie_char_new(&c2, "b", "b", "ab", 2) != CANGJIE_OK
            || cangjie_char_list_prepend(&l, c2) != CANGJIE_OK
            || l->c != c2 || l->next->c != c1) {
            fprintf(stderr, "char_list_prepend failed\n");
            cangjie_char_list_free(l);
            return 1;
        }
        cangjie_char_list_free(l);
    }
    printf("CHECK-OK: char_list\n");

    /* 5: open database handle */
    Cangjie *cj = NULL;
    int ret = cangjie_new(&cj, CANGJIE_VERSION_3, CANGJIE_FILTER_BIG5);
    if (ret != CANGJIE_OK || cj == NULL) {
        fprintf(stderr, "cangjie_new failed: %d (is CANGJIE_DB set?)\n", ret);
        return 1;
    }
    if (cj->version != CANGJIE_VERSION_3) {
        fprintf(stderr, "version field mismatch\n");
        cangjie_free(cj);
        return 1;
    }
    printf("CHECK-OK: cangjie_new\n");

    /* 6: real query against cangjie.db (wildcard keeps it robust) */
    {
        CangjieCharList *chars = NULL;
        ret = cangjie_get_characters(cj, "d*d", &chars);
        if (ret != CANGJIE_OK || chars == NULL || chars->c == NULL
            || chars->c->chchar == NULL || strlen(chars->c->chchar) == 0) {
            fprintf(stderr, "get_characters failed: %d\n", ret);
            cangjie_free(cj);
            return 1;
        }
        printf("CHECK-OK: get_characters %s %s\n", chars->c->chchar,
               chars->c->code ? chars->c->code : "");
        cangjie_char_list_free(chars);
    }

    cangjie_free(cj);
    printf("ALL CHECKS PASSED\n");
    return 0;
}
