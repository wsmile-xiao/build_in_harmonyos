#include <stddef.h>
#include <stdint.h>
#include <jbig2.h>
#include <stdio.h>

int main(void) {
    static const unsigned char header[] = {
        0x97, 0x4a, 0x42, 0x32, 0x0d, 0x0a, 0x1a, 0x0a, 0x03
    };
    Jbig2Ctx *ctx = jbig2_ctx_new(NULL, 0, NULL, NULL, NULL);
    if (!ctx) {
        fprintf(stderr, "jbig2_ctx_new failed\n");
        return 1;
    }
    if (jbig2_data_in(ctx, header, sizeof(header)) != 0) {
        fprintf(stderr, "jbig2_data_in rejected a valid file header\n");
        jbig2_ctx_free(ctx);
        return 1;
    }
    jbig2_ctx_free(ctx);
    printf("jbig2dec: context and data input APIs ok\n");
    return 0;
}
