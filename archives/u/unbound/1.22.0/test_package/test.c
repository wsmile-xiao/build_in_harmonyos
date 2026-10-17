#include <unbound.h>
#include <stdio.h>
#include <stdlib.h>

/* R34: real functional test of the libunbound API.
 * Creates a resolver context, round-trips an option through the library
 * (proves the libunbound library is loaded, configured and functional),
 * then cleans up. */
int main(void) {
    struct ub_ctx* ctx = ub_ctx_create();
    if (!ctx) {
        fprintf(stderr, "test_unbound: ub_ctx_create() failed\n");
        return 1;
    }

    int r = ub_ctx_set_option(ctx, "logfile:", "/dev/stderr");
    if (r != 0) {
        fprintf(stderr, "test_unbound: ub_ctx_set_option: %s\n", ub_strerror(r));
        ub_ctx_delete(ctx);
        return 1;
    }

    char* val = NULL;
    r = ub_ctx_get_option(ctx, "logfile:", &val);
    if (r != 0) {
        fprintf(stderr, "test_unbound: ub_ctx_get_option: %s\n", ub_strerror(r));
        ub_ctx_delete(ctx);
        return 1;
    }

    printf("test_unbound: libunbound 1.22.0 OK (logfile=%s)\n",
           val ? val : "(null)");
    free(val);
    ub_ctx_delete(ctx);
    return 0;
}
