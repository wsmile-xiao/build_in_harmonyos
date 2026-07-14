/* test.c — zlib-ng-compat L1 smoke test
 * Verifies that the standard zlib API is available and works.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

int main(void) {
    const char *version = zlibVersion();
    printf("zlib version: %s\n", version);

    /* Test basic compress/deflate API */
    const char *test_input = "Hello, zlib-ng-compat!";
    unsigned long src_len = strlen(test_input) + 1;
    unsigned long dest_len = compressBound(src_len);
    unsigned char *compressed = (unsigned char *)malloc(dest_len);
    if (!compressed) {
        fprintf(stderr, "FAIL: malloc(compressed) failed\n");
        return 1;
    }
    unsigned char *decompressed = (unsigned char *)malloc(src_len);
    if (!decompressed) {
        fprintf(stderr, "FAIL: malloc(decompressed) failed\n");
        free(compressed);
        return 1;
    }

    /* Compress */
    int ret = compress(compressed, &dest_len,
                       (const unsigned char *)test_input, src_len);
    if (ret != Z_OK) {
        fprintf(stderr, "FAIL: compress() returned %d\n", ret);
        return 1;
    }
    printf("compress OK (src=%lu -> dest=%lu)\n", src_len, dest_len);

    /* Decompress */
    ret = uncompress(decompressed, &src_len, compressed, dest_len);
    if (ret != Z_OK) {
        fprintf(stderr, "FAIL: uncompress() returned %d\n", ret);
        return 1;
    }

    if (strcmp((const char *)decompressed, test_input) != 0) {
        fprintf(stderr, "FAIL: decompressed data mismatch: '%s'\n",
                (const char *)decompressed);
        return 1;
    }
    printf("uncompress OK: '%s'\n", (const char *)decompressed);

    free(compressed);
    free(decompressed);

    printf("PASS: zlib-ng-compat API is functional\n");
    return 0;
}