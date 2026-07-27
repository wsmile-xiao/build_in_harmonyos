/*
 * test_libstemmer.c — L1 consumer test for libstemmer
 *
 * Creates an English stemmer, stems "connected" and "running",
 * verifies the results are "connect" and "run" respectively.
 */
#include <stdio.h>
#include <string.h>
#include "libstemmer.h"

int main(void)
{
    struct sb_stemmer *stemmer;
    const sb_symbol *result;
    int errors = 0;

    /* Create an English stemmer (UTF-8) */
    stemmer = sb_stemmer_new("english", "UTF_8");
    if (stemmer == NULL) {
        fprintf(stderr, "FAIL: sb_stemmer_new(\"english\", \"UTF_8\") returned NULL\n");
        return 1;
    }

    /* Test 1: "connected" should stem to "connect" */
    result = sb_stemmer_stem(stemmer, (const sb_symbol *)"connected", 9);
    if (result == NULL) {
        fprintf(stderr, "FAIL: sb_stemmer_stem(\"connected\") returned NULL\n");
        sb_stemmer_delete(stemmer);
        return 1;
    }
    int len = sb_stemmer_length(stemmer);
    if (len != 7 || strncmp((const char *)result, "connect", 7) != 0) {
        fprintf(stderr, "FAIL: stem(\"connected\") = \"%.*s\", expected \"connect\"\n", len, result);
        errors++;
    } else {
        printf("PASS: stem(\"connected\") = \"connect\"\n");
    }

    /* Test 2: "running" should stem to "run" */
    result = sb_stemmer_stem(stemmer, (const sb_symbol *)"running", 7);
    if (result == NULL) {
        fprintf(stderr, "FAIL: sb_stemmer_stem(\"running\") returned NULL\n");
        sb_stemmer_delete(stemmer);
        return 1;
    }
    len = sb_stemmer_length(stemmer);
    if (len != 3 || strncmp((const char *)result, "run", 3) != 0) {
        fprintf(stderr, "FAIL: stem(\"running\") = \"%.*s\", expected \"run\"\n", len, result);
        errors++;
    } else {
        printf("PASS: stem(\"running\") = \"run\"\n");
    }

    /* Test 3: Verify sb_stemmer_list returns non-NULL */
    const char **list = sb_stemmer_list();
    if (list == NULL) {
        fprintf(stderr, "FAIL: sb_stemmer_list() returned NULL\n");
        errors++;
    } else {
        /* Count available algorithms */
        int count = 0;
        while (list[count] != NULL) count++;
        printf("PASS: sb_stemmer_list() returned %d algorithms\n", count);
    }

    sb_stemmer_delete(stemmer);

    if (errors > 0) {
        fprintf(stderr, "FAIL: %d test(s) failed\n", errors);
        return 1;
    }

    printf("All tests passed.\n");
    return 0;
}
