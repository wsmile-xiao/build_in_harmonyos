#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "libdeflate.h"

int main(void)
{
    const char *input = "libdeflate 1.22 HarmonyOS consumer test";
    size_t input_size = strlen(input);
    struct libdeflate_compressor *compressor = libdeflate_alloc_compressor(6);
    if (!compressor) {
        return 1;
    }

    size_t bound = libdeflate_deflate_compress_bound(compressor, input_size);
    unsigned char *compressed = malloc(bound);
    if (!compressed) {
        libdeflate_free_compressor(compressor);
        return 1;
    }
    size_t compressed_size = libdeflate_deflate_compress(
        compressor, input, input_size, compressed, bound);
    libdeflate_free_compressor(compressor);
    if (compressed_size == 0) {
        free(compressed);
        return 1;
    }

    struct libdeflate_decompressor *decompressor = libdeflate_alloc_decompressor();
    char *output = malloc(input_size + 1);
    if (!decompressor || !output) {
        libdeflate_free_decompressor(decompressor);
        free(compressed);
        free(output);
        return 1;
    }

    size_t output_size = 0;
    enum libdeflate_result result = libdeflate_deflate_decompress(
        decompressor, compressed, compressed_size, output, input_size, &output_size);
    libdeflate_free_decompressor(decompressor);
    free(compressed);
    output[output_size] = '\0';

    if (result != LIBDEFLATE_SUCCESS || output_size != input_size ||
        memcmp(output, input, input_size) != 0) {
        free(output);
        return 1;
    }
    printf("libdeflate 1.22 roundtrip passed (%zu -> %zu bytes)\n",
           input_size, output_size);
    free(output);
    return 0;
}
