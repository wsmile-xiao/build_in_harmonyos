#include <stdio.h>
#define PCRE2_CODE_UNIT_WIDTH 8
#include <pcre2.h>

int main(void) {
    int errorcode;
    PCRE2_SIZE erroroffset;
    /* Compile a simple pattern */
    pcre2_code *re = pcre2_compile((PCRE2_SPTR)"hello", 5, 0,
                                    &errorcode, &erroroffset, NULL);
    if (re == NULL) {
        printf("pcre2_compile failed\n");
        return 1;
    }
    /* Match against a string */
    pcre2_match_data *match_data = pcre2_match_data_create_from_pattern(re, NULL);
    if (match_data == NULL) {
        printf("pcre2_match_data_create_from_pattern failed\n");
        pcre2_code_free(re);
        return 1;
    }
    int rc = pcre2_match(re, (PCRE2_SPTR)"hello world", 11, 0, 0, match_data, NULL);
    pcre2_match_data_free(match_data);
    pcre2_code_free(re);
    if (rc < 0) {
        printf("pcre2_match failed (rc=%d)\n", rc);
        return 1;
    }
    printf("pcre2 test: matched %d substrings\n", rc);
    return 0;
}
