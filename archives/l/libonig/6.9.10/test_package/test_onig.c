#include <stdio.h>
#include <string.h>

#include "oniguruma.h"

static int fail(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(void)
{
    const UChar pattern[] = "(\\p{Han}+)([0-9]+)";
    const UChar text[] = {0xe9, 0xb8, 0xbf, 0xe8, 0x92, 0x99, '6', 0};
    const UChar invalid_pattern[] = "[";
    OnigEncoding encoding = ONIG_ENCODING_UTF8;
    OnigErrorInfo error_info;
    OnigRegion *region = NULL;
    regex_t *regex = NULL;
    int result;

    if (onig_initialize(&encoding, 1) != 0) {
        return fail("onig_initialize failed");
    }
    if (strcmp(onig_version(), "6.9.10") != 0) {
        onig_end();
        return fail("unexpected Oniguruma version");
    }

    result = onig_new(&regex, pattern, pattern + sizeof(pattern) - 1,
                      ONIG_OPTION_DEFAULT, ONIG_ENCODING_UTF8,
                      ONIG_SYNTAX_DEFAULT, &error_info);
    if (result != ONIG_NORMAL) {
        onig_end();
        return fail("UTF-8 expression compilation failed");
    }

    region = onig_region_new();
    if (!region) {
        onig_free(regex);
        onig_end();
        return fail("region allocation failed");
    }
    result = onig_search(regex, text, text + sizeof(text) - 1, text,
                         text + sizeof(text) - 1, region, ONIG_OPTION_NONE);
    if (result < 0 || region->num_regs < 3
        || region->beg[0] != 0 || region->end[0] != 7
        || region->beg[1] != 0 || region->end[1] != 6
        || region->beg[2] != 6 || region->end[2] != 7) {
        onig_region_free(region, 1);
        onig_free(regex);
        onig_end();
        return fail("UTF-8 match or capture offsets are incorrect");
    }

    onig_region_free(region, 1);
    onig_free(regex);
    regex = NULL;
    result = onig_new(&regex, invalid_pattern,
                      invalid_pattern + sizeof(invalid_pattern) - 1,
                      ONIG_OPTION_DEFAULT, ONIG_ENCODING_UTF8,
                      ONIG_SYNTAX_DEFAULT, &error_info);
    if (result >= 0 || regex != NULL) {
        if (regex != NULL) {
            onig_free(regex);
        }
        onig_end();
        return fail("invalid expression was accepted");
    }

    onig_end();
    puts("PASS: Oniguruma UTF-8 API, captures, version, and error handling");
    return 0;
}
