#include <stddef.h>
#include <stdio.h>

#include <pcre2.h>

#define CHECK(condition, message)                                              \
    do {                                                                       \
        if (!(condition)) {                                                    \
            fprintf(stderr, "check failed: %s\n", (message));               \
            return 1;                                                          \
        }                                                                      \
    } while (0)

int main(void)
{
    static const PCRE2_UCHAR pattern[] = {
        '^', 'h', 'e', 'l', 'l', 'o', '-', '(', '[', '0', '-', '9', ']',
        '+', ')', '$', 0
    };
    static const PCRE2_UCHAR subject[] = {
        'h', 'e', 'l', 'l', 'o', '-', '2', '0', '4', '7', 0
    };
    int error_code = 0;
    PCRE2_SIZE error_offset = 0;
    pcre2_code *code = pcre2_compile(
        pattern, PCRE2_ZERO_TERMINATED, 0, &error_code, &error_offset, NULL);
    CHECK(code != NULL, "compile pattern");

    CHECK(pcre2_jit_compile(code, PCRE2_JIT_COMPLETE) == 0, "compile JIT code");

    pcre2_match_data *match_data = pcre2_match_data_create_from_pattern(code, NULL);
    CHECK(match_data != NULL, "allocate match data");

    int match_count = pcre2_match(
        code, subject, PCRE2_ZERO_TERMINATED, 0, 0, match_data, NULL);
    CHECK(match_count == 2, "match full expression and capture");

    PCRE2_SIZE *ovector = pcre2_get_ovector_pointer(match_data);
    CHECK(ovector != NULL, "read match offsets");
    CHECK(ovector[0] == 0 && ovector[1] == 10, "validate full match offsets");
    CHECK(ovector[2] == 6 && ovector[3] == 10, "validate capture offsets");

    PCRE2_UCHAR *capture = NULL;
    PCRE2_SIZE capture_length = 0;
    CHECK(
        pcre2_substring_get_bynumber(match_data, 1, &capture, &capture_length) == 0,
        "extract capture");
    CHECK(capture_length == 4, "validate capture length");
    CHECK(
        capture[0] == '2' && capture[1] == '0' &&
            capture[2] == '4' && capture[3] == '7',
        "validate capture contents");

    pcre2_substring_free(capture);
    pcre2_match_data_free(match_data);
    pcre2_code_free(code);
    return 0;
}
