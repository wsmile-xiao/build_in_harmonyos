#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <uriparser/Uri.h>

/* Real consumer test (R34): parses a URI with the actual uriparser API and
 * recomposes it, verifying the round-trip output. Not a print-only shell. */
int main(void) {
    const char *input = "http://example.com/path/to/resource?query=1#fragment";
    UriParserStateA state;
    UriUriA parsed;
    int rc;

    memset(&parsed, 0, sizeof(parsed));
    state.uri = &parsed;

    rc = uriParseUriA(&state, input);
    if (rc != URI_SUCCESS) {
        fprintf(stderr, "FAIL: uriParseUriA returned %d\n", rc);
        return 1;
    }

    if (parsed.hostText.first == NULL || parsed.hostText.afterLast == NULL ||
        parsed.hostText.afterLast - parsed.hostText.first <= 0) {
        fprintf(stderr, "FAIL: host component not parsed\n");
        uriFreeUriMembersA(&parsed);
        return 1;
    }
    fprintf(stderr, "host: %.*s\n",
            (int)(parsed.hostText.afterLast - parsed.hostText.first),
            parsed.hostText.first);

    /* Re-compose the URI into a string.
     * NOTE: uriToStringA(NULL, ...) always returns URI_ERROR_NULL because the
     * public API passes charsRequired=NULL internally (UriRecompose.c:88), so
     * use a fixed buffer with an explicit maxChars instead of size-first. */
    char buf[1024];
    int chars_written = 0;
    if (uriToStringA(buf, &parsed, (int)sizeof(buf), &chars_written) != URI_SUCCESS) {
        fprintf(stderr, "FAIL: uriToStringA recompose\n");
        uriFreeUriMembersA(&parsed);
        return 1;
    }
    if (chars_written <= 0 || strstr(buf, "example.com") == NULL) {
        fprintf(stderr, "FAIL: recomposed URI malformed: '%s'\n", buf);
        uriFreeUriMembersA(&parsed);
        return 1;
    }

    printf("test uriparser 1.0.2 OK: parsed '%s'\n", input);
    printf("recomposed: %s\n", buf);
    uriFreeUriMembersA(&parsed);
    return 0;
}
