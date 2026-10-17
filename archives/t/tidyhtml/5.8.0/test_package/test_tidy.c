/* test_package/test_tidy.c — tidyhtml 5.8.0 consumer test.
 * Real libtidy API roundtrip: create -> parse string -> clean/repair ->
 * save to buffer -> verify content. Each check prints a PASS line so the
 * harness counts genuine assertions (a stub binary prints none). */
#include <stdio.h>
#include <string.h>
#include <tidy.h>
#include <tidybuffio.h>

int main(void) {
    TidyDoc tdoc = tidyCreate();
    if (!tdoc) {
        fprintf(stderr, "CASE FAIL: tidyCreate returned NULL\n");
        return 1;
    }
    printf("CASE PASS: tidyCreate\n");

    TidyBuffer errbuf = {0};
    TidyBuffer output = {0};
    tidySetErrorBuffer(tdoc, &errbuf);

    const char *input = "<p>Hello tidy 5.8.0</p>";
    int rc = tidyParseString(tdoc, input);
    if (rc < 0) {
        fprintf(stderr, "CASE FAIL: tidyParseString rc=%d\n", rc);
        tidyRelease(tdoc);
        return 1;
    }
    printf("CASE PASS: tidyParseString rc=%d\n", rc);

    rc = tidyCleanAndRepair(tdoc);
    if (rc < 0) {
        fprintf(stderr, "CASE FAIL: tidyCleanAndRepair rc=%d\n", rc);
        tidyBufFree(&errbuf);
        tidyRelease(tdoc);
        return 1;
    }
    printf("CASE PASS: tidyCleanAndRepair rc=%d\n", rc);

    rc = tidySaveBuffer(tdoc, &output);
    if (rc < 0 || output.bp == NULL || output.size == 0) {
        fprintf(stderr, "CASE FAIL: tidySaveBuffer rc=%d size=%u\n", rc, output.size);
        tidyBufFree(&errbuf);
        tidyBufFree(&output);
        tidyRelease(tdoc);
        return 1;
    }
    printf("CASE PASS: tidySaveBuffer size=%u\n", output.size);

    if (strstr((const char *)output.bp, "Hello tidy") == NULL) {
        fprintf(stderr, "CASE FAIL: output missing expected text: %s\n", (const char *)output.bp);
        tidyBufFree(&errbuf);
        tidyBufFree(&output);
        tidyRelease(tdoc);
        return 1;
    }
    printf("CASE PASS: output content verified\n");

    tidyBufFree(&errbuf);
    tidyBufFree(&output);
    tidyRelease(tdoc);
    return 0;
}
