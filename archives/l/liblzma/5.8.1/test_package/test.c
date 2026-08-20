#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <lzma.h>

int main(void) {
    const char *input = "Hello, liblzma! This is a test of LZMA2 compression.";
    size_t input_len = strlen(input);

    uint8_t compressed[1024];
    size_t out_pos = 0;

    /* Compress */
    lzma_ret ret = lzma_easy_buffer_encode(LZMA_PRESET_DEFAULT,
        LZMA_CHECK_CRC64, NULL,
        (const uint8_t *)input, input_len,
        compressed, &out_pos, sizeof(compressed));
    if (ret != LZMA_OK) {
        fprintf(stderr, "Compression failed: %d\n", ret);
        return 1;
    }

    size_t compressed_len = out_pos;

    /* Decompress */
    uint8_t decompressed[1024];
    size_t in_pos = 0;
    size_t decomp_pos = 0;
    size_t memlimit = UINT64_MAX;

    ret = lzma_stream_buffer_decode(&memlimit, 0, NULL,
        compressed, &in_pos, compressed_len,
        decompressed, &decomp_pos, sizeof(decompressed));
    if (ret != LZMA_OK) {
        fprintf(stderr, "Decompression failed: %d\n", ret);
        return 1;
    }

    /* Verify round-trip */
    if (decomp_pos != input_len ||
        memcmp(decompressed, input, input_len) != 0) {
        fprintf(stderr, "Round-trip mismatch!\n");
        return 1;
    }

    printf("liblzma 5.8.1: compress %zu -> %zu bytes, round-trip OK\n",
        input_len, compressed_len);
    return 0;
}
