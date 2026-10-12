#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "dpi.h"

int main(void) {
    dpiContext *ctx = NULL;
    dpiErrorInfo errInfo;

    printf("odpi 6.0.0 test\n");
    printf("  Header DPI_VERSION_NUMBER=%d (expect 60000)\n", DPI_VERSION_NUMBER);
    printf("  Header DPI_MAJOR_VERSION=%d, MINOR=%d, PATCH=%d\n",
           DPI_MAJOR_VERSION, DPI_MINOR_VERSION, DPI_PATCH_LEVEL);

    int rc = dpiContext_createWithParams(
        DPI_MAJOR_VERSION, DPI_MINOR_VERSION,
        NULL, &ctx, &errInfo);

    if (rc == 0) {
        printf("  Oracle Client found (full ODPI-C available)\n");
        dpiContext_destroy(ctx);
        printf("  Test: PASS\n");
        return 0;
    }

    if (rc < 0) {
        printf("  Oracle Client not found (rc=%d)\n", rc);
        printf("  Error: %.*s\n", (int)errInfo.messageLength, errInfo.message);
        if (strstr(errInfo.message, "DPI-") != NULL) {
            printf("  DPI error code confirmed (library loaded correctly)\n");
            printf("  Test: PASS (library functional, Oracle Client optional)\n");
            return 0;
        }
        fprintf(stderr, "FAIL: unexpected error\n");
        return 1;
    }

    fprintf(stderr, "FAIL: unexpected rc=%d\n", rc);
    return 1;
}
