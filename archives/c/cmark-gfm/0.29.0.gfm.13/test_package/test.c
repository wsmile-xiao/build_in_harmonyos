#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <cmark-gfm.h>

int main(void) {
    const char *markdown = "# Hello World\n\nThis is **cmark-gfm**!\n";
    char *html = cmark_markdown_to_html(markdown, strlen(markdown), 0);

    if (!html) {
        fprintf(stderr, "ERROR: cmark_markdown_to_html returned NULL\n");
        return 1;
    }

    printf("Input markdown:\n%s\n", markdown);
    printf("Output HTML:\n%s\n", html);

    free(html);
    return 0;
}
