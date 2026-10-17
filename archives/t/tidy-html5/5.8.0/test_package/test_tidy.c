/* test_package/test_tidy.c — tidy-html5 5.8.0 L1 smoke test.
 * Tidy a simple HTML string and verify the output. */
#include <stdio.h>
#include <string.h>
#include <tidy.h>
#include <tidybuffio.h>

int main(void) {
    TidyDoc tdoc = tidyCreate();
    if (!tdoc) {
        fprintf(stderr, "tidyCreate() returned NULL\n");
        return 1;
    }
    TidyBuffer errbuf = {0};
    int rc = -1;

    /* Set error buffer to capture diagnostics */
    tidySetErrorBuffer(tdoc, &errbuf);

    /* Parse a simple HTML string */
    const char *input = "<p>Hello tidy 5.8.0</p>";

    TidyBuffer output = {0};
    rc = tidyParseString(tdoc, input);
    if (rc < 0) {
        fprintf(stderr, "Parse failed: rc=%d\n", rc);
        tidyRelease(tdoc);
        tidyBufFree(&errbuf);
        tidyBufFree(&output);
        return 1;
    }

    /* Clean and repair */
    rc = tidyCleanAndRepair(tdoc);
    if (rc < 0) {
        fprintf(stderr, "CleanAndRepair failed: rc=%d\n", rc);
        tidyRelease(tdoc);
        tidyBufFree(&errbuf);
        tidyBufFree(&output);
        return 1;
    }

    /* Save to buffer */
    rc = tidySaveBuffer(tdoc, &output);
    if (rc < 0) {
        fprintf(stderr, "SaveBuffer failed: rc=%d\n", rc);
        tidyRelease(tdoc);
        tidyBufFree(&errbuf);
        tidyBufFree(&output);
        return 1;
    }

    /* Verify output contains expected text */
    if (strstr((const char *)output.bp, "Hello tidy") == NULL) {
        fprintf(stderr, "Output missing expected text: %s\n", output.bp);
        tidyRelease(tdoc);
        tidyBufFree(&errbuf);
        tidyBufFree(&output);
        return 1;
    }

    printf("tidy-html5 5.8.0: parse/clean/serialize roundtrip OK\n");
    tidyRelease(tdoc);
    tidyBufFree(&errbuf);
    tidyBufFree(&output);
    return 0;
}
