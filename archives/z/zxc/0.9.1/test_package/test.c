#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Include zxc header to verify headers are properly installed */
#include <zxc.h>

int main(void) {
    /* Simple compression round-trip test */
    const char *input = "Hello, zxc compression world! This is a test message.";
    size_t input_len = strlen(input);

    /* Get max compressed size */
    uint64_t max_compressed = zxc_compress_bound(input_len);

    /* Allocate buffers */
    unsigned char *compressed = (unsigned char *)malloc(max_compressed);
    unsigned char *decompressed = (unsigned char *)malloc(input_len + 1);

    if (!compressed || !decompressed) {
        printf("Memory allocation failed\n");
        free(compressed);
        free(decompressed);
        return 1;
    }

    /* Compress */
    zxc_compress_opts_t opts = {0};
    opts.level = 3;
    opts.checksum_enabled = 1;

    int64_t compressed_size = zxc_compress(input, input_len, compressed, max_compressed, &opts);

    if (compressed_size <= 0) {
        printf("Compression failed (code: %lld)\n", (long long)compressed_size);
        free(compressed);
        free(decompressed);
        return 1;
    }

    printf("Compressed %zu -> %lld bytes\n", input_len, (long long)compressed_size);

    /* Decompress */
    zxc_decompress_opts_t dopts = {0};
    dopts.checksum_enabled = 1;

    int64_t decompressed_size = zxc_decompress(compressed, (size_t)compressed_size,
                                               decompressed, input_len, &dopts);

    if (decompressed_size != (int64_t)input_len) {
        printf("Decompression size mismatch: %lld != %zu\n", (long long)decompressed_size, input_len);
        free(compressed);
        free(decompressed);
        return 1;
    }

    decompressed[decompressed_size] = '\0';

    if (memcmp(input, decompressed, input_len) != 0) {
        printf("Data mismatch after round-trip\n");
        free(compressed);
        free(decompressed);
        return 1;
    }

    printf("test zxc 0.9.1: OK (round-trip verified)\n");

    free(compressed);
    free(decompressed);
    return 0;
}
