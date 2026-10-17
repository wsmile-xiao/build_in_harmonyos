/* test.c — libestr API smoke test (R34: must call real API) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "libestr.h"

int main(void) {
    /* Get library version */
    char *ver = es_version();
    if (ver == NULL) {
        fprintf(stderr, "FAIL: es_version() returned NULL\n");
        return 1;
    }
    printf("libestr version: %s\n", ver);

    /* Create a string from a C string */
    es_str_t *s = es_newStrFromCStr("hello", 5);
    if (s == NULL) {
        fprintf(stderr, "FAIL: es_newStrFromCStr returned NULL\n");
        return 1;
    }

    /* Check string length */
    es_size_t len = es_strlen(s);
    if (len != 5) {
        fprintf(stderr, "FAIL: es_strlen returned %u, expected 5\n", len);
        es_deleteStr(s);
        return 1;
    }

    /* Convert back to C string */
    char *cstr = es_str2cstr(s, NULL);
    if (cstr == NULL) {
        fprintf(stderr, "FAIL: es_str2cstr returned NULL\n");
        es_deleteStr(s);
        return 1;
    }
    if (strcmp(cstr, "hello") != 0) {
        fprintf(stderr, "FAIL: es_str2cstr returned '%s', expected 'hello'\n", cstr);
        free(cstr);
        es_deleteStr(s);
        return 1;
    }
    printf("String round-trip OK: '%s' (len=%u)\n", cstr, len);
    free(cstr);

    /* Compare against a buffer */
    int cmp = es_strbufcmp(s, (const unsigned char *)"hello", 5);
    if (cmp != 0) {
        fprintf(stderr, "FAIL: es_strbufcmp returned %d, expected 0\n", cmp);
        es_deleteStr(s);
        return 1;
    }

    /* Clean up */
    es_deleteStr(s);

    printf("test libestr 0.1.11: OK\n");
    return 0;
}
