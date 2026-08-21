/* test_package/test.c — smoke test for the avce00 library.
 *
 * Links against libavce00 and exercises the E00 reader open/close path
 * and the public AVC_VERSION macro.  No test data files are needed:
 * we verify that the API correctly reports errors for nonexistent input.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "avc.h"

int main(void) {
    /* 1. Verify the AVC_VERSION macro is present and matches 2.x */
    printf("[test] AVC_VERSION = %s\n", AVC_VERSION);
    if (strncmp(AVC_VERSION, "2.", 2) != 0) {
        fprintf(stderr, "FAIL: expected AVC_VERSION starting with '2.', got '%s'\n",
                AVC_VERSION);
        return 1;
    }
    printf("OK: AVC_VERSION starts with '2.'\n");

    /* 2. Verify E00 reader returns NULL for a nonexistent file */
    {
        AVCE00ReadPtr psInfo = AVCE00ReadOpen("/nonexistent/path/e00");
        if (psInfo != NULL) {
            fprintf(stderr, "FAIL: AVCE00ReadOpen returned non-NULL for bogus path\n");
            AVCE00ReadClose(psInfo);
            return 2;
        }
        printf("OK: AVCE00ReadOpen(NULL) for nonexistent path\n");
    }

    /* 3. Verify E00 writer returns NULL for a read-only path */
    {
        AVCE00WritePtr psInfo = AVCE00WriteOpen("/nonexistent/path/e00",
                                                 AVCCoverV7, 0);
        if (psInfo != NULL) {
            fprintf(stderr, "FAIL: AVCE00WriteOpen returned non-NULL for bogus path\n");
            AVCE00WriteClose(psInfo);
            return 3;
        }
        printf("OK: AVCE00WriteOpen(NULL) for nonexistent path\n");
    }

    puts("avce00 API assertions: 3 passed");
    return 0;
}
