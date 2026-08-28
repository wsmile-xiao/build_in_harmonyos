/*
 * test_lowdown.c — C API conversion test for lowdown
 *
 * Parses a small Markdown document and renders it to HTML via the
 * high-level lowdown_buf() API, then asserts the output contains the
 * expected <h1> heading.  Exits 0 on success, 1 on failure.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/queue.h>   /* TAILQ_HEAD — needed by lowdown.h */

#include <lowdown.h>

int main(void)
{
    static const char md[] = "# Hello from lowdown\n\n"
                            "A **bold** paragraph.\n";

    struct lowdown_opts opts;
    char *out = NULL;
    size_t outsz = 0;
    int rc;

    memset(&opts, 0, sizeof(opts));
    opts.type = LOWDOWN_HTML;
    opts.maxdepth = 128;
    opts.feat =
        LOWDOWN_ATTRS |
        LOWDOWN_AUTOLINK |
        LOWDOWN_COMMONMARK |
        LOWDOWN_DEFLIST |
        LOWDOWN_FENCED |
        LOWDOWN_FOOTNOTES |
        LOWDOWN_MATH |
        LOWDOWN_METADATA |
        LOWDOWN_STRIKE |
        LOWDOWN_SUPER |
        LOWDOWN_TABLES |
        LOWDOWN_TASKLIST;

    rc = lowdown_buf(&opts, md, sizeof(md) - 1, &out, &outsz, NULL);
    if (rc != 1 || out == NULL) {
        fprintf(stderr, "FAIL: lowdown_buf returned %d\n", rc);
        free(out);
        return 1;
    }

    /* Write the HTML output so it's visible in CI logs */
    fwrite(out, 1, outsz, stdout);
    fputc('\n', stdout);

    const char *h1 = strstr(out, "<h1");
    if (h1 == NULL || strstr(h1, ">Hello from lowdown</h1>") == NULL) {
        fprintf(stderr, "FAIL: expected <h1> heading not found in output\n");
        free(out);
        return 1;
    }

    free(out);
    printf("OK: C API Markdown->HTML conversion succeeded\n");
    return 0;
}
