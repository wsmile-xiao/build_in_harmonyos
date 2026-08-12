/* test.c - zlib-ng L1 smoke test (native API, ZLIB_COMPAT=OFF) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib-ng.h>

int main(void) {
    printf("zlib-ng version: %s\n", ZLIBNG_VERSION);

    const char *test_input = "Hello, zlib-ng!";
    size_t src_len = strlen(test_input) + 1;
    size_t dest_len = zng_compressBound(src_len);
    unsigned char *compressed = (unsigned char *)malloc(dest_len);
    if (!compressed) { fprintf(stderr, "FAIL: malloc\n"); return 1; }
    unsigned char *decompressed = (unsigned char *)malloc(src_len);
    if (!decompressed) { fprintf(stderr, "FAIL: malloc\n"); free(compressed); return 1; }

    int ret = zng_compress(compressed, &dest_len,
                           (const unsigned char *)test_input, src_len);
    if (ret != Z_OK) {
        fprintf(stderr, "FAIL: zng_compress()=%d\n", ret);
        free(compressed); free(decompressed); return 1;
    }
    printf("zng_compress OK (src=%zu -> dest=%zu)\n", src_len, dest_len);

    size_t out_len = src_len;
    ret = zng_uncompress(decompressed, &out_len, compressed, dest_len);
    if (ret != Z_OK) {
        fprintf(stderr, "FAIL: zng_uncompress()=%d\n", ret);
        free(compressed); free(decompressed); return 1;
    }

    if (strcmp((const char *)decompressed, test_input) != 0) {
        fprintf(stderr, "FAIL: data mismatch\n");
        free(compressed); free(decompressed); return 1;
    }
    printf("zng_uncompress OK: '%s'\n", (const char *)decompressed);

    free(compressed);
    free(decompressed);
    printf("PASS: zlib-ng native API is functional\n");
    return 0;
}
