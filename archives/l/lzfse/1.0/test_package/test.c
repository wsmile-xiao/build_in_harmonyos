#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "lzfse.h"

int main(void) {
    const char *input = "LZFSE is a compression algorithm developed by Apple. "
                        "It provides fast compression and decompression. "
                        "This test verifies the round-trip functionality.";
    size_t input_len = strlen(input);

    /* Allocate buffers */
    size_t dst_size = input_len + 256;
    uint8_t *compressed = (uint8_t *)malloc(dst_size);
    uint8_t *decompressed = (uint8_t *)malloc(input_len + 1);

    if (!compressed || !decompressed) {
        fprintf(stderr, "FAIL: Memory allocation failed\n");
        free(compressed);
        free(decompressed);
        return 1;
    }

    /* Encode */
    size_t compressed_size = lzfse_encode_buffer(compressed, dst_size,
                                                  (const uint8_t *)input, input_len, NULL);
    if (compressed_size == 0) {
        fprintf(stderr, "FAIL: Encoding failed\n");
        free(compressed);
        free(decompressed);
        return 1;
    }

    /* Decode */
    size_t decompressed_size = lzfse_decode_buffer(decompressed, input_len,
                                                    compressed, compressed_size, NULL);
    if (decompressed_size == 0) {
        fprintf(stderr, "FAIL: Decoding failed\n");
        free(compressed);
        free(decompressed);
        return 1;
    }

    /* Verify round-trip */
    if (decompressed_size == input_len && memcmp(input, decompressed, input_len) == 0) {
        printf("PASS: Round-trip OK (%zu -> %zu -> %zu bytes)\n",
               input_len, compressed_size, decompressed_size);
        free(compressed);
        free(decompressed);
        return 0;
    } else {
        fprintf(stderr, "FAIL: Data mismatch (expected %zu, got %zu)\n",
                input_len, decompressed_size);
        free(compressed);
        free(decompressed);
        return 1;
    }
}
