/*
 * test_xz.c — LZMA compress/decompress round-trip test for liblzma.
 *
 * Consumer test (R34): links against the packaged liblzma, uses
 * lzma_easy_buffer_encode + lzma_stream_buffer_decode to verify that the
 * library works correctly on the target platform.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <lzma.h>

int main(void) {
    const char *input = "Hello, xz 5.8.3! LZMA compress/decompress round-trip test on HarmonyOS PC.";
    size_t in_size = strlen(input);

    /* Compress */
    size_t out_size = in_size + 1024;  /* plenty of room for small input */
    unsigned char *compressed = (unsigned char *)malloc(out_size);
    if (!compressed) {
        fprintf(stderr, "malloc failed\n");
        return 1;
    }

    size_t out_pos = 0;
    lzma_ret ret = lzma_easy_buffer_encode(
        LZMA_PRESET_DEFAULT, LZMA_CHECK_CRC64,
        NULL,
        (const uint8_t *)input, in_size,
        compressed, &out_pos, out_size);
    if (ret != LZMA_OK) {
        fprintf(stderr, "lzma_easy_buffer_encode failed: %d\n", ret);
        free(compressed);
        return 1;
    }

    printf("Compressed %zu bytes to %zu bytes\n", in_size, out_pos);

    /* Decompress */
    unsigned char *decompressed = (unsigned char *)malloc(in_size + 1);
    if (!decompressed) {
        fprintf(stderr, "malloc failed\n");
        free(compressed);
        return 1;
    }

    size_t in_pos = 0;
    size_t dec_pos = 0;
    uint64_t memlimit = UINT64_MAX;
    ret = lzma_stream_buffer_decode(
        &memlimit, 0, NULL,
        compressed, &in_pos, out_pos,
        decompressed, &dec_pos, in_size);
    if (ret != LZMA_OK) {
        fprintf(stderr, "lzma_stream_buffer_decode failed: %d\n", ret);
        free(compressed);
        free(decompressed);
        return 1;
    }

    decompressed[dec_pos] = '\0';

    /* Verify round-trip */
    if (dec_pos != in_size || memcmp(decompressed, input, in_size) != 0) {
        fprintf(stderr, "round-trip data mismatch\n");
        free(compressed);
        free(decompressed);
        return 1;
    }

    printf("Decompressed %zu bytes — round-trip OK\n", dec_pos);
    printf("liblzma version: %s\n", lzma_version_string());
    free(compressed);
    free(decompressed);
    return 0;
}
