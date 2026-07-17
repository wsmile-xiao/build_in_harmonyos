#include <stdio.h>
#include <stdlib.h>

#define PCRE2_CODE_UNIT_WIDTH 8
#include <pcre2.h>

int main(void) {
    int errorcode;
    PCRE2_SIZE erroroffset;
    int rc;

    pcre2_code *re = pcre2_compile(
        (PCRE2_SPTR)"hello",
        PCRE2_ZERO_TERMINATED,
        0,
        &errorcode,
        &erroroffset,
        NULL
    );
    if (re == NULL) {
        printf("pcre2_compile failed\n");
        return 1;
    }

    pcre2_match_data *match_data = pcre2_match_data_create_from_pattern(re, NULL);
    if (match_data == NULL) {
        printf("pcre2_match_data_create_from_pattern failed\n");
        pcre2_code_free(re);
        return 1;
    }
    rc = pcre2_match(re, (PCRE2_SPTR)"hello world", 11, 0, 0, match_data, NULL);

    if (rc >= 0) {
        printf("test pcre2 10.40: OK (matched at offset 0)\n");
    } else {
        printf("test pcre2 10.40: FAIL (no match, rc=%d)\n", rc);
        pcre2_match_data_free(match_data);
        pcre2_code_free(re);
        return 1;
    }

    pcre2_match_data_free(match_data);
    pcre2_code_free(re);
    return 0;
}
