/*
 * test_package consumer — lwprintf 1.1.0
 *
 * A genuine consumer of the installed package: uses only the public
 * header "lwprintf/lwprintf.h" and the public API lwprintf_snprintf(),
 * verifies the observable formatted output, and exits non-zero on
 * mismatch.
 */
#include <stdio.h>
#include <string.h>
#include "lwprintf/lwprintf.h"

int
main(void) {
    char buffer[64];

    /* Format via the public API and verify observable output */
    int len = lwprintf_snprintf(buffer, sizeof(buffer), "Hello %s, %d", "world", 42);
    if (len != 15 || strcmp(buffer, "Hello world, 42") != 0) {
        fprintf(stderr, "FAIL: len=%d buffer='%s'\n", len, buffer);
        return 1;
    }

    /* Float formatting, another public-API path */
    len = lwprintf_snprintf(buffer, sizeof(buffer), "%.2f", 3.14159);
    if (len != 4 || strcmp(buffer, "3.14") != 0) {
        fprintf(stderr, "FAIL: len=%d buffer='%s'\n", len, buffer);
        return 2;
    }

    printf("test lwprintf 1.1.0: OK\n");
    return 0;
}