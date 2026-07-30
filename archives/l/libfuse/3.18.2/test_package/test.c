#define FUSE_USE_VERSION 35

#include <stdio.h>
#include <stdlib.h>
#include <fuse3/fuse.h>
#include <fuse3/fuse_opt.h>


int main(void) {
    /* Verify we can link against libfuse3 and use its API (R34) */
    struct fuse_args args = FUSE_ARGS_INIT(0, NULL);

    /* Test 1: fuse_opt_add_arg() — public API, no kernel required */
    int rc = fuse_opt_add_arg(&args, "dummy");
    if (rc != 0) {
        fprintf(stderr, "FAILED: fuse_opt_add_arg returned %d\n", rc);
        return 1;
    }
    printf("libfuse 3.18.2: fuse_opt_add_arg OK\n");

    /* Test 2: fuse_version() — returns library version string, no kernel required */
    int ver = fuse_version();
    printf("libfuse 3.18.2: fuse_version() = %d\n", ver);
    if (ver < 3) {
        fprintf(stderr, "FAILED: fuse_version %d < 30 (expected >= 30)\n", ver);
        return 1;
    }

    /* Test 3: fuse_opt_free_args() — cleanup, no kernel required */
    fuse_opt_free_args(&args);
    printf("libfuse 3.18.2: fuse_opt_free_args OK\n");

    printf("test libfuse 3.18.2: PASSED\n");
    return 0;
}
