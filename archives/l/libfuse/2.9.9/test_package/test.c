/*
 * test.c — libfuse 2.9.9 test_package (R34: calls real API)
 *
 * Calls fuse_version() to verify the library links and the symbol is
 * available. Does not attempt to mount (OHOS lacks FUSE kernel support
 * in most containers).
 */
#include <stdio.h>
#include <stdlib.h>
#include <fuse.h>

int main(void)
{
    int ver = fuse_version();
    /* libfuse 2.9.9 → FUSE API version 26 */
    if (ver <= 0) {
        fprintf(stderr, "FAIL: fuse_version() returned %d\n", ver);
        return EXIT_FAILURE;
    }
    printf("OK: libfuse linked, fuse_version() = %d\n", ver);
    return EXIT_SUCCESS;
}
