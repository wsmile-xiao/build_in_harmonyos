#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "lzlib.h"

#define EXPECT(condition, name)                                        \
    do {                                                               \
        ++checks_run;                                                  \
        if (!(condition)) {                                            \
            fprintf(stderr, "FAIL: %s\n", name);                    \
            goto cleanup;                                              \
        }                                                              \
    } while (0)

int main(void) {
    const char *input = "Hello, lzlib! This is a consumer round-trip test.";
    const int input_len = (int)strlen(input);
    uint8_t compressed[1024];
    uint8_t decompressed[1024];
    int comp_len = 0;
    int decomp_len = 0;
    int ret;
    int checks_run = 0;
    LZ_Encoder *encoder = NULL;
    LZ_Decoder *decoder = NULL;
    int result = 1;

    EXPECT(LZ_version() != NULL && strcmp(LZ_version(), "1.16") == 0,
           "version string is 1.16");
    EXPECT(LZ_api_version() >= 1016, "runtime API version is at least 1016");

    encoder = LZ_compress_open(65535, 16, INT64_MAX);
    EXPECT(encoder != NULL && LZ_compress_errno(encoder) == LZ_ok,
           "compression encoder opens");
    EXPECT(LZ_compress_write(encoder, (const uint8_t *)input, input_len) == input_len,
           "encoder accepts the complete input");
    LZ_compress_finish(encoder);

    while (LZ_compress_finished(encoder) != 1) {
        if (comp_len >= (int)sizeof(compressed)) {
            fprintf(stderr, "FAIL: compressed data exceeds test buffer\n");
            goto cleanup;
        }
        ret = LZ_compress_read(encoder, compressed + comp_len,
                               (int)sizeof(compressed) - comp_len);
        if (ret < 0) {
            fprintf(stderr, "FAIL: LZ_compress_read returned an error\n");
            goto cleanup;
        }
        comp_len += ret;
    }
    EXPECT(comp_len > 0 && LZ_compress_finished(encoder) == 1,
           "compression completes with output");
    LZ_compress_close(encoder);
    encoder = NULL;

    decoder = LZ_decompress_open();
    EXPECT(decoder != NULL && LZ_decompress_errno(decoder) == LZ_ok,
           "decompression decoder opens");
    EXPECT(LZ_decompress_write(decoder, compressed, comp_len) == comp_len,
           "decoder accepts the complete compressed input");
    LZ_decompress_finish(decoder);

    while (LZ_decompress_finished(decoder) != 1) {
        if (decomp_len >= (int)sizeof(decompressed)) {
            fprintf(stderr, "FAIL: decompressed data exceeds test buffer\n");
            goto cleanup;
        }
        ret = LZ_decompress_read(decoder, decompressed + decomp_len,
                                 (int)sizeof(decompressed) - decomp_len);
        if (ret < 0) {
            fprintf(stderr, "FAIL: LZ_decompress_read returned an error\n");
            goto cleanup;
        }
        decomp_len += ret;
    }
    EXPECT(LZ_decompress_finished(decoder) == 1,
           "decompression completes");
    EXPECT(decomp_len == input_len && memcmp(input, decompressed, input_len) == 0,
           "decompressed bytes equal the original input");

    result = 0;

cleanup:
    if (encoder != NULL) {
        LZ_compress_close(encoder);
    }
    if (decoder != NULL) {
        LZ_decompress_close(decoder);
    }
    if (result == 0) {
        printf("Consumer checks: %d/9 passed\n", checks_run);
    }
    return result;
}
