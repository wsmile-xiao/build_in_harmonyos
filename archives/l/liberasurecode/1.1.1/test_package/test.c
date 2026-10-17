#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <erasurecode.h>
#include <erasurecode_stdinc.h>

int main(void) {
    struct ec_args args;
    int desc = -1;
    int rc = 0;

    memset(&args, 0, sizeof(args));
    args.k = 2;
    args.m = 1;
    args.ct = CHKSUM_NONE;

    /* Create an erasure code instance with the built-in NULL backend. */
    desc = liberasurecode_instance_create(EC_BACKEND_NULL, &args);
    if (desc < 0) {
        fprintf(stderr, "liberasurecode_instance_create failed: %d\n", desc);
        return 1;
    }
    rc = liberasurecode_instance_destroy(desc);
    if (rc != 0) {
        fprintf(stderr, "liberasurecode_instance_destroy failed: %d\n", rc);
        return 1;
    }
    printf("test liberasurecode 1.1.1: OK\n");
    return 0;
}
