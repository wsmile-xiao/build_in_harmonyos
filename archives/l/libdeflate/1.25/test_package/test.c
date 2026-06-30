/* test_package/test.c — libdeflate 1.25 L1 smoke test.
 * Exercises the public C API: compress + decompress roundtrip. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "libdeflate.h"

int main(void) {
    const char *input = "hello libdeflate 1.25 roundtrip test";
    size_t in_len = strlen(input);

    /* Compress */
    struct libdeflate_compressor *c = libdeflate_alloc_compressor(6);
    if (!c) { fprintf(stderr, "alloc_compressor failed\n"); return 1; }

    size_t bound = libdeflate_deflate_compress_bound(c, in_len);
    if (bound == 0) { fprintf(stderr, "compress_bound=0\n"); libdeflate_free_compressor(c); return 1; }

    unsigned char *out = malloc(bound);
    if (!out) { libdeflate_free_compressor(c); return 1; }

    size_t out_len = libdeflate_deflate_compress(c, input, in_len, out, bound);
    libdeflate_free_compressor(c);
    if (out_len == 0) { fprintf(stderr, "compress produced 0 bytes\n"); free(out); return 1; }

    /* Decompress */
    struct libdeflate_decompressor *d = libdeflate_alloc_decompressor();
    if (!d) { fprintf(stderr, "alloc_decompressor failed\n"); free(out); return 1; }

    char *back = malloc(in_len + 1);
    if (!back) { libdeflate_free_decompressor(d); free(out); return 1; }

    size_t actual = 0;
    int rc = libdeflate_deflate_decompress(d, out, out_len, back, in_len, &actual);
    libdeflate_free_decompressor(d);
    free(out);

    if (rc != LIBDEFLATE_SUCCESS) {
        fprintf(stderr, "decompress failed: rc=%d\n", rc);
        free(back);
        return 1;
    }
    back[actual] = '\0';

    if (actual != in_len || memcmp(back, input, in_len) != 0) {
        fprintf(stderr, "roundtrip mismatch: got '%s'\n", back);
        free(back);
        return 1;
    }
    free(back);

    printf("test libdeflate 1.25: compress(%zuB)->decompress(%zuB) roundtrip OK\n",
           in_len, out_len);
    return 0;
}
