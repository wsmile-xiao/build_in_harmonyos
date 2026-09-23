/* test_fuzzy.c — libfuzzy2 consumer test (R34: calls real API). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "fuzzy.h"

static int check(int cond, const char *label)
{
    if (!cond) {
        fprintf(stderr, "FAIL: %s\n", label);
        return 1;
    }
    printf("ok: %s\n", label);
    return 0;
}

int main(void)
{
    char result1[FUZZY_MAX_RESULT];
    char result2[FUZZY_MAX_RESULT];
    char result3[FUZZY_MAX_RESULT];
    int failures = 0;

    /* Assertion 1: hash a buffer of realistic size. */
    static unsigned char buf[4096];
    size_t i;
    for (i = 0; i < sizeof(buf); i++) {
        buf[i] = (unsigned char)((i * 31 + 7) & 0xFF);
    }
    memset(result1, 0, sizeof(result1));
    failures += check(fuzzy_hash_buf(buf, (uint32_t)sizeof(buf), result1) == 0,
                      "fuzzy_hash_buf succeeds");
    failures += check(result1[0] != '\0', "hash output non-empty");

    /* Assertion 2: hash a file written to the current (writable) directory. */
    {
        FILE *fp = fopen("hmbs_fuzzy_input.bin", "wb");
        if (fp == NULL) {
            fprintf(stderr, "FAIL: cannot create temp input file\n");
            return 1;
        }
        fwrite(buf, 1, sizeof(buf), fp);
        fclose(fp);
        memset(result3, 0, sizeof(result3));
        failures += check(fuzzy_hash_filename("hmbs_fuzzy_input.bin", result3) == 0,
                          "fuzzy_hash_filename succeeds");
        failures += check(result3[0] != '\0', "file hash output non-empty");
        remove("hmbs_fuzzy_input.bin");
    }

    /* Assertion 3: identical signatures compare at 100. */
    failures += check(fuzzy_compare(result1, result1) == 100,
                      "fuzzy_compare identical == 100");

    /* Assertion 4: near-identical input is comparable (no error). */
    buf[100] ^= 0xFF;
    buf[200] ^= 0xFF;
    memset(result2, 0, sizeof(result2));
    failures += check(fuzzy_hash_buf(buf, (uint32_t)sizeof(buf), result2) == 0,
                      "fuzzy_hash_buf on modified buffer succeeds");
    {
        int score = fuzzy_compare(result1, result2);
        failures += check(score >= 0, "fuzzy_compare similar returns score");
        printf("similarity score: %d\n", score);
    }

    if (failures == 0) {
        printf("test libfuzzy2 2.14.1: OK\n");
        return 0;
    }
    fprintf(stderr, "test libfuzzy2 2.14.1: %d assertion(s) failed\n", failures);
    return 1;
}
