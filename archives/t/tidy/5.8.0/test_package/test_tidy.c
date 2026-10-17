/* Consumer test for libtidy: parse, clean and repair an HTML document
 * through the library API. */
#include <stdio.h>
#include <string.h>
#include <tidy.h>
#include <tidybuffio.h>

static const char *GOOD_HTML =
    "<!DOCTYPE html>\n<html><head><title>t</title></head>\n"
    "<body><p>hello</p></body></html>\n";

int main(void)
{
    TidyDoc doc = tidyCreate();
    TidyBuffer out;
    int rc;

    if (!doc) {
        fprintf(stderr, "FAIL: tidyCreate returned NULL\n");
        return 1;
    }

    /* 1. option access works */
    if (tidySetCharEncoding(doc, "utf8") < 0) {
        fprintf(stderr, "FAIL: tidySetCharEncoding\n");
        return 1;
    }

    /* 2. parse a well-formed document */
    rc = tidyParseString(doc, GOOD_HTML);
    if (rc < 0) {
        fprintf(stderr, "FAIL: tidyParseString rc=%d\n", rc);
        return 1;
    }

    /* 3. clean and repair, then the output must contain markup */
    memset(&out, 0, sizeof(out));
    if (tidyCleanAndRepair(doc) < 0) {
        fprintf(stderr, "FAIL: tidyCleanAndRepair\n");
        return 1;
    }
    if (tidySaveBuffer(doc, &out) < 0) {
        fprintf(stderr, "FAIL: tidySaveBuffer\n");
        return 1;
    }
    if (!out.bp || !strstr((const char *)out.bp, "<html>")) {
        fprintf(stderr, "FAIL: repaired output missing <html>\n");
        tidyBufFree(&out);
        return 1;
    }
    tidyBufFree(&out);

    /* 4. error count on well-formed input is zero */
    if (tidyErrorCount(doc) != 0) {
        fprintf(stderr, "FAIL: tidyErrorCount=%d on valid doc\n",
                tidyErrorCount(doc));
        return 1;
    }

    tidyRelease(doc);
    printf("tidy library consumer test: PASS\n");
    return 0;
}
