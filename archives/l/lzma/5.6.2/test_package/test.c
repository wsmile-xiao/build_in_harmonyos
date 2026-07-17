#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <lzma.h>

int main(void) {
    /* Verify version string is accessible */
    const char *version = lzma_version_string();
    if (version[0] == '\0') {
        fprintf(stderr, "FAIL: lzma_version_string returned empty\n");
        return 1;
    }
    printf("lzma version: %s\n", version);

    /* Simple compression round-trip test */
    const char *input = "Hello HarmonyOS from lzma!";
    size_t input_len = strlen(input) + 1; /* include null terminator */

    uint8_t outbuf[256];
    size_t out_pos = 0;

    lzma_ret ret = lzma_easy_buffer_encode(
        LZMA_PRESET_DEFAULT, LZMA_CHECK_CRC64,
        NULL,
        (const uint8_t *)input, input_len,
        outbuf, &out_pos, sizeof(outbuf));

    if (ret != LZMA_OK) {
        fprintf(stderr, "FAIL: lzma_easy_buffer_encode returned %d\n", ret);
        return 1;
    }
    printf("Compressed %zu bytes -> %zu bytes\n", input_len, out_pos);

    /* Decompress */
    uint8_t decbuf[256];
    size_t dec_pos = 0;
    size_t in_pos = 0;
    uint64_t memlimit = UINT64_MAX;

    ret = lzma_stream_buffer_decode(
        &memlimit, 0, NULL,
        outbuf, &in_pos, out_pos,
        decbuf, &dec_pos, sizeof(decbuf));

    if (ret != LZMA_OK) {
        fprintf(stderr, "FAIL: lzma_stream_buffer_decode returned %d\n", ret);
        return 1;
    }

    if (dec_pos != input_len || memcmp(decbuf, input, input_len) != 0) {
        fprintf(stderr, "FAIL: decompressed data mismatch\n");
        return 1;
    }

    printf("Decompressed OK: %s\n", (char *)decbuf);
    printf("test lzma 5.6.2: OK\n");
    return 0;
}
