/*
 * Snappy consumer smoke test — compress and decompress a string,
 * verify the round-trip matches.
 */
#include <snappy-c.h>
#include <string.h>
#include <stdio.h>

int main(void) {
    const char* input = "Hello, Snappy! This is a test string for compression.";
    size_t input_len = strlen(input);

    /* Compress */
    size_t compressed_len = snappy_max_compressed_length(input_len);
    char compressed[256];
    snappy_status rc = snappy_compress(input, input_len, compressed, &compressed_len);
    if (rc != SNAPPY_OK) {
        fprintf(stderr, "snappy_compress failed: %d\n", rc);
        return 1;
    }

    /* Decompress */
    char decompressed[256];
    size_t decompressed_len = sizeof(decompressed);
    rc = snappy_uncompress(compressed, compressed_len, decompressed, &decompressed_len);
    if (rc != SNAPPY_OK) {
        fprintf(stderr, "snappy_uncompress failed: %d\n", rc);
        return 1;
    }

    /* Verify round-trip */
    if (decompressed_len != input_len ||
        memcmp(decompressed, input, input_len) != 0) {
        fprintf(stderr, "Round-trip mismatch!\n");
        return 1;
    }

    printf("Snappy round-trip OK: compressed %zu -> %zu bytes\n",
           input_len, compressed_len);
    return 0;
}
