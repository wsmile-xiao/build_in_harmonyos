#include <stdio.h>
#include <stdlib.h>
#include <strophe.h>

int main(void) {
    xmpp_initialize();
    if (!xmpp_version_check(0, 14)) {
        fprintf(stderr, "libstrophe version check failed\n");
        return 1;
    }
    xmpp_ctx_t *ctx = xmpp_ctx_new(NULL, NULL);
    if (ctx == NULL) {
        fprintf(stderr, "xmpp_ctx_new returned NULL\n");
        xmpp_shutdown();
        return 1;
    }
    xmpp_ctx_set_verbosity(ctx, 0);
    xmpp_ctx_free(ctx);
    xmpp_shutdown();
    printf("test libstrophe 0.14.0: OK\n");
    return 0;
}