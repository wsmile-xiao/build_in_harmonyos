/* test_package/test.c — substantively tests discount library API (R34) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mkdio.h>

int main(void) {
    const char *input = "# Hello World\n\nThis is a **test**.\n";
    MMIOT *doc = mkd_string(input, (int)strlen(input), 0);
    if (!doc) {
        fprintf(stderr, "FAIL: mkd_string returned NULL\n");
        return 1;
    }
    if (mkd_compile(doc, 0) == 0) {
        fprintf(stderr, "FAIL: mkd_compile failed\n");
        mkd_cleanup(doc);
        return 1;
    }
    char *html = NULL;
    int sz = mkd_document(doc, &html);
    if (sz <= 0 || html == NULL) {
        fprintf(stderr, "FAIL: mkd_document returned empty\n");
        mkd_cleanup(doc);
        return 1;
    }
    /* Verify the output contains expected HTML */
    if (strstr(html, "<h1>Hello World</h1>") == NULL) {
        fprintf(stderr, "FAIL: expected <h1> not found in output\n");
        fprintf(stderr, "Got: %.*s\n", sz, html);
        mkd_cleanup(doc);
        return 1;
    }
    printf("OK: discount markdown conversion works\n");
    printf("Output: %.*s", sz, html);
    mkd_cleanup(doc);
    return 0;
}
