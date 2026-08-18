#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "lzlib.h"

int main(void) {
    const char *input = "Hello, lzlib! This is a test of LZMA compression.";
    int input_len = (int)strlen(input);
    uint8_t compressed[1024];
    uint8_t decompressed[1024];
    int comp_len = 0, decomp_len = 0;
    int ret;

    /* Compress */
    LZ_Encoder *encoder = LZ_compress_open(65535, 16, INT64_MAX);
    if (!encoder || LZ_compress_errno(encoder) != LZ_ok) {
        fprintf(stderr, "ERROR: LZ_compress_open failed\n");
        return 1;
    }

    ret = LZ_compress_write(encoder, (const uint8_t *)input, input_len);
    if (ret != input_len) {
        fprintf(stderr, "ERROR: LZ_compress_write failed\n");
        LZ_compress_close(encoder);
        return 1;
    }
    LZ_compress_finish(encoder);

    while (1) {
        ret = LZ_compress_read(encoder, compressed + comp_len, sizeof(compressed) - comp_len);
        if (ret < 0) {
            fprintf(stderr, "ERROR: LZ_compress_read failed\n");
            LZ_compress_close(encoder);
            return 1;
        }
        comp_len += ret;
        if (LZ_compress_finished(encoder) == 1) break;
    }
    LZ_compress_close(encoder);

    /* Decompress */
    LZ_Decoder *decoder = LZ_decompress_open();
    if (!decoder || LZ_decompress_errno(decoder) != LZ_ok) {
        fprintf(stderr, "ERROR: LZ_decompress_open failed\n");
        return 1;
    }

    ret = LZ_decompress_write(decoder, compressed, comp_len);
    if (ret != comp_len) {
        fprintf(stderr, "ERROR: LZ_decompress_write failed\n");
        LZ_decompress_close(decoder);
        return 1;
    }
    LZ_decompress_finish(decoder);

    while (1) {
        ret = LZ_decompress_read(decoder, decompressed + decomp_len, sizeof(decompressed) - decomp_len);
        if (ret < 0) {
            fprintf(stderr, "ERROR: LZ_decompress_read failed\n");
            LZ_decompress_close(decoder);
            return 1;
        }
        decomp_len += ret;
        if (LZ_decompress_finished(decoder) == 1) break;
    }
    LZ_decompress_close(decoder);

    /* Verify */
    if (decomp_len != input_len || memcmp(input, decompressed, input_len) != 0) {
        fprintf(stderr, "ERROR: Decompressed data differs from original\n");
        return 1;
    }

    printf("lzlib %s: compress/decompress test PASSED\n", LZ_version());
    return 0;
}
