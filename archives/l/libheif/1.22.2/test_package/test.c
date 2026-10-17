/* test_package/test.c — libheif 1.22.2 L1 smoke test.
 * Exercises the public C API: context alloc/free + version query. */
#include <stdio.h>
#include <string.h>

#include "libheif/heif.h"

int main(void) {
    /* Query library version */
    const char *version = heif_get_version();
    if (!version || strlen(version) == 0) {
        fprintf(stderr, "heif_get_version returned empty\n");
        return 1;
    }
    printf("libheif version: %s\n", version);

    /* Allocate and free a context */
    struct heif_context *ctx = heif_context_alloc();
    if (!ctx) {
        fprintf(stderr, "heif_context_alloc failed\n");
        return 1;
    }
    heif_context_free(ctx);

    printf("libheif 1.22.2 smoke test OK\n");
    return 0;
}
