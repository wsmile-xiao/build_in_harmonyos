#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libMultiMarkdown.h>

int main(void) {
    char *html = mmd_string_convert("*hi*\n", EXT_SMART | EXT_NOTES, FORMAT_HTML, ENGLISH);
    if (html == NULL) {
        fprintf(stderr, "mmd_string_convert returned NULL\n");
        return 1;
    }
    if (strstr(html, "<em>hi</em>") == NULL) {
        fprintf(stderr, "unexpected HTML: %s\n", html);
        free(html);
        return 1;
    }
    free(html);
    printf("test multimarkdown 6.6.0: OK\n");
    return 0;
}
