/* Consumer test for libGringotts — exercises the real encrypt/decrypt API. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <libgringotts.h>

int main(void) {
    unsigned char *ver = grg_get_version();
    printf("libgringotts version: %s\n", ver ? (char *)ver : "(null)");
    if (!ver || strstr((char *)ver, "1.2.1") == NULL) {
        printf("FAIL: unexpected version string\n");
        return 1;
    }

    const unsigned char *header = (const unsigned char *)"GRG";
    GRG_CTX ctx = grg_context_initialize_defaults(header);
    if (!ctx) {
        printf("FAIL: grg_context_initialize_defaults returned NULL\n");
        return 1;
    }

    const unsigned char *pwd = (const unsigned char *)"s3cr3t-passwd";
    GRG_KEY key = grg_key_gen(pwd, (int)strlen((const char *)pwd));
    if (!key) {
        printf("FAIL: grg_key_gen returned NULL\n");
        grg_context_free(ctx);
        return 1;
    }

    const unsigned char *plain =
        (const unsigned char *)"Hello, libGringotts! 0123456789 ABCDEFGHIJ";
    long dim = (long)strlen((const char *)plain);
    const char *path = "grg_test.dat";

    int rc = grg_encrypt_file(ctx, key, (const unsigned char *)path, plain, dim);
    if (rc != GRG_OK) {
        printf("FAIL: grg_encrypt_file rc=%d\n", rc);
        grg_key_free(ctx, key);
        grg_context_free(ctx);
        return 1;
    }

    unsigned char *out = NULL;
    long outdim = 0;
    rc = grg_decrypt_file(ctx, key, (const unsigned char *)path, &out, &outdim);
    if (rc != GRG_OK) {
        printf("FAIL: grg_decrypt_file rc=%d\n", rc);
        grg_key_free(ctx, key);
        grg_context_free(ctx);
        return 1;
    }

    if (outdim != dim || memcmp(out, plain, dim) != 0) {
        printf("FAIL: roundtrip mismatch (outdim=%ld expected=%ld)\n", outdim, dim);
        grg_free(ctx, out, outdim);
        grg_key_free(ctx, key);
        grg_context_free(ctx);
        return 1;
    }

    grg_free(ctx, out, outdim);
    grg_key_free(ctx, key);
    grg_context_free(ctx);
    printf("OK: libgringotts encrypt/decrypt roundtrip verified (%ld bytes)\n", dim);
    return 0;
}
