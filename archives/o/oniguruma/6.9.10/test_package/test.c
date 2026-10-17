#include <stdio.h>
#include <string.h>
#include <oniguruma.h>

int main(void)
{
    int r;
    regex_t *reg;
    OnigErrorInfo einfo;

    r = onig_init();
    if (r != ONIG_NORMAL) {
        fprintf(stderr, "onig_init failed: %d\n", r);
        return 1;
    }

    OnigUChar *pattern = (OnigUChar *)"\\w+";
    OnigUChar *str = (OnigUChar *)"hello world";

    r = onig_new(&reg, pattern, pattern + strlen((char *)pattern),
                 ONIG_OPTION_DEFAULT, ONIG_ENCODING_UTF8, ONIG_SYNTAX_DEFAULT, &einfo);
    if (r != ONIG_NORMAL) {
        OnigUChar s[ONIG_MAX_ERROR_MESSAGE_LEN];
        onig_error_code_to_str(s, r);
        fprintf(stderr, "onig_new failed: %s\n", s);
        onig_end();
        return 1;
    }

    OnigRegion *region = onig_region_new();
    if (!region) {
        fprintf(stderr, "onig_region_new failed\n");
        onig_free(reg);
        onig_end();
        return 1;
    }
    int end = (int)strlen((char *)str);
    r = onig_search(reg, str, str + end, str, str + end, region, ONIG_OPTION_NONE);
    if (r >= 0) {
        printf("match at %d, length %d\n", r, region->end[0] - region->beg[0]);
    } else {
        printf("no match (ret=%d)\n", r);
        onig_region_free(region, 1);
        onig_free(reg);
        onig_end();
        return 1;
    }

    onig_region_free(region, 1);
    onig_free(reg);
    onig_end();
    return 0;
}
