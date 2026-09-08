#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <oniguruma.h>

/* 消费者验证：使用 oniguruma 真实 API 编译链接并执行一次正则匹配 */
int main(void) {
    OnigEncoding enc = ONIG_ENCODING_UTF8;
    regex_t *reg;
    OnigErrorInfo einfo;
    OnigRegion *region;
    const char *pattern = "^ab+c$";
    const char *str = "abbbc";
    int r;

    r = onig_new(&reg, (const OnigUChar *)pattern,
                 (const OnigUChar *)(pattern + strlen(pattern)),
                 ONIG_OPTION_DEFAULT, enc, ONIG_SYNTAX_DEFAULT, &einfo);
    if (r != ONIG_NORMAL) {
        OnigUChar s[ONIG_MAX_ERROR_MESSAGE_LEN];
        onig_error_code_to_str(s, r, &einfo);
        fprintf(stderr, "onig_new failed: %s\n", (char *)s);
        return 1;
    }

    region = onig_region_new();
    r = onig_search(reg, (const OnigUChar *)str, (const OnigUChar *)(str + strlen(str)),
                    (const OnigUChar *)str, (const OnigUChar *)(str + strlen(str)),
                    region, ONIG_OPTION_NONE);
    if (r < 0) {
        fprintf(stderr, "onig_search failed: r=%d\n", r);
        onig_region_free(region, 1);
        onig_free(reg);
        onig_end();
        return 1;
    }

    printf("consumer test: match at [%d,%d) length=%d\n",
           region->beg[0], region->end[0], region->end[0] - region->beg[0]);

    onig_region_free(region, 1);
    onig_free(reg);
    onig_end();
    return 0;
}
