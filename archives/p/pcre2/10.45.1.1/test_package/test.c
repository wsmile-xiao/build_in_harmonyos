#include <stdio.h>

#define PCRE2_CODE_UNIT_WIDTH 8
#include <pcre2.h>

int main(void) {
    static const PCRE2_UCHAR pattern[] = "^hello ([a-z]+)$";
    static const PCRE2_UCHAR subject[] = "hello world";
    int error_code = 0;
    PCRE2_SIZE error_offset = 0;
    pcre2_code *code = pcre2_compile(pattern, PCRE2_ZERO_TERMINATED, 0,
                                     &error_code, &error_offset, NULL);
    if (code == NULL) {
        fprintf(stderr, "pcre2_compile failed: code=%d offset=%zu\n",
                error_code, (size_t)error_offset);
        return 1;
    }

    pcre2_match_data *match_data = pcre2_match_data_create_from_pattern(code, NULL);
    if (match_data == NULL) {
        fprintf(stderr, "pcre2_match_data_create_from_pattern failed\n");
        pcre2_code_free(code);
        return 1;
    }

    int result = pcre2_match(code, subject, PCRE2_ZERO_TERMINATED, 0, 0,
                             match_data, NULL);
    if (result != 2) {
        fprintf(stderr, "pcre2_match returned %d, expected 2 captures\n", result);
        pcre2_match_data_free(match_data);
        pcre2_code_free(code);
        return 1;
    }

    PCRE2_SIZE *ovector = pcre2_get_ovector_pointer(match_data);
    if (ovector[0] != 0 || ovector[1] != 11 ||
        ovector[2] != 6 || ovector[3] != 11) {
        fprintf(stderr, "unexpected match ranges: %zu-%zu, %zu-%zu\n",
                (size_t)ovector[0], (size_t)ovector[1],
                (size_t)ovector[2], (size_t)ovector[3]);
        pcre2_match_data_free(match_data);
        pcre2_code_free(code);
        return 1;
    }

    pcre2_match_data_free(match_data);
    pcre2_code_free(code);
    puts("pcre2 consumer test passed: full=0-11 capture=6-11");
    return 0;
}
