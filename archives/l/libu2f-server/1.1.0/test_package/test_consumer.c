/*
 * Consumer program for libu2f-server — read-only API test.
 *
 * Calls u2fs_init / u2fs_done which do not require hardware.
 * Returns 0 on success, 1 on failure.
 */
#include <stdio.h>
#include <u2f-server/u2f-server.h>

int main(void)
{
    struct u2fs_init_ctx *ctx = NULL;
    u2fs_rc rc;

    rc = u2fs_init(&ctx);
    if (rc != U2FS_OK) {
        fprintf(stderr, "u2fs_init failed rc=%d\n", rc);
        return 1;
    }

    printf("u2fs_init ok\n");

    u2fs_done(ctx);
    printf("consumer PASS\n");
    return 0;
}
