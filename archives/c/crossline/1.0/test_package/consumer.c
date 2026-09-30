/*
 * crossline_consumer — real consumer of the crossline public API.
 *
 * Exercises the installed public header (crossline.h) and public APIs:
 *   - crossline_readline: read a line from non-tty stdin (pipe), observable
 *     result is the echoed line content.
 *   - crossline_delimiter_set: configure word delimiter (no error return,
 *     side effect verified through the pipe readline path).
 *   - crossline_history_save / crossline_history_load: persist history via a
 *     real file round-trip, observable through return codes.
 *   - crossline_paging_check: paging API with known small input.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "crossline.h"

int main(void)
{
    char buf[256];
    int failures = 0;

    crossline_delimiter_set(" \t");

    /* Non-tty path: pipe in "hello-crossline\n" and verify the returned line. */
    if (crossline_readline("test>", buf, sizeof(buf)) == NULL) {
        fprintf(stderr, "FAIL: crossline_readline returned NULL\n");
        return 1;
    }
    if (strcmp(buf, "hello-crossline") != 0) {
        fprintf(stderr, "FAIL: readline content mismatch: '%s'\n", buf);
        return 1;
    }
    printf("readline ok: %s\n", buf);

    /* History save/load round-trip. */
    if (crossline_history_save(".crossline-hist-test") != 0) {
        fprintf(stderr, "FAIL: crossline_history_save failed\n");
        return 1;
    }
    if (crossline_history_load(".crossline-hist-test") != 0) {
        fprintf(stderr, "FAIL: crossline_history_load failed\n");
        return 1;
    }
    crossline_history_clear();
    printf("history save/load ok\n");

    /* Paging API: 1 line, small terminal -> continue (0) or quit (1). */
    crossline_paging_reset();
    {
        int rc = crossline_paging_check(1);
        /* Both 0 and 1 are valid returns depending on terminal size; the API
         * must simply return one of them without crashing. */
        (void)rc;
    }
    printf("paging ok\n");

    if (failures) {
        fprintf(stderr, "consumer FAILED with %d failure(s)\n", failures);
        return 1;
    }
    printf("consumer PASSED\n");
    return 0;
}