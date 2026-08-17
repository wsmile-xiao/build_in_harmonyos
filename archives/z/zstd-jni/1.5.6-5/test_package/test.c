#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <zstd.h>

int main(void) {
    unsigned int ver = ZSTD_versionNumber();
    printf("ZSTD version number: %u\n", ver);

    const char *input = "Hello, zstd-jni! Compression and decompression roundtrip test.";
    size_t input_len = strlen(input);

    size_t bound = ZSTD_compressBound(input_len);
    void *compressed = malloc(bound);
    if (!compressed) {
        fprintf(stderr, "malloc failed\n");
        return 1;
    }

    size_t csize = ZSTD_compress(compressed, bound, input, input_len, 3);
    if (ZSTD_isError(csize)) {
        fprintf(stderr, "compress failed\n");
        free(compressed);
        return 1;
    }
    printf("Compressed %zu -> %zu bytes\n", input_len, csize);

    void *decompressed = malloc(input_len);
    if (!decompressed) {
        fprintf(stderr, "malloc failed\n");
        free(compressed);
        return 1;
    }

    size_t dsize = ZSTD_decompress(decompressed, input_len, compressed, csize);
    if (ZSTD_isError(dsize)) {
        fprintf(stderr, "decompress failed\n");
        free(compressed);
        free(decompressed);
        return 1;
    }
    printf("Decompressed %zu -> %zu bytes\n", csize, dsize);

    if (dsize == input_len && memcmp(input, decompressed, input_len) == 0) {
        printf("Roundtrip OK: zstd-jni 1.5.6-5 functional test passed\n");
        free(compressed);
        free(decompressed);
        return 0;
    } else {
        fprintf(stderr, "Roundtrip mismatch!\n");
        free(compressed);
        free(decompressed);
        return 1;
    }
}
