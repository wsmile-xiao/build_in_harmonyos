/* Consumer tests for libdeflate/1.26 across DEFLATE, zlib, and gzip APIs. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "libdeflate.h"

static unsigned checks;
static unsigned failures;

#define CHECK(condition, label) do { \
    ++checks; \
    if (condition) { \
        printf("PASS %s\n", label); \
    } else { \
        fprintf(stderr, "FAIL %s\n", label); \
        ++failures; \
    } \
} while (0)

int main(void)
{
    static const char input[] = "HarmonyOS consumer round-trip: libdeflate/1.26";
    const size_t input_size = sizeof(input) - 1;
    struct libdeflate_compressor *compressor = libdeflate_alloc_compressor(6);
    struct libdeflate_decompressor *decompressor = libdeflate_alloc_decompressor();
    unsigned char decoded[sizeof(input)];
    size_t actual;
    size_t bound;
    size_t compressed_size;
    unsigned char *compressed;
    enum libdeflate_result result;

    CHECK(compressor != NULL, "allocate compressor");
    CHECK(decompressor != NULL, "allocate decompressor");
    if (!compressor || !decompressor)
        goto done;

    bound = libdeflate_deflate_compress_bound(compressor, input_size);
    CHECK(bound > 0, "DEFLATE compression bound");
    compressed = bound ? malloc(bound) : NULL;
    CHECK(compressed != NULL, "allocate DEFLATE output");
    if (!compressed)
        goto done;
    compressed_size = libdeflate_deflate_compress(compressor, input, input_size, compressed, bound);
    CHECK(compressed_size > 0, "DEFLATE compression");
    actual = 0;
    result = libdeflate_deflate_decompress(decompressor, compressed, compressed_size,
                                           decoded, sizeof(decoded), &actual);
    CHECK(result == LIBDEFLATE_SUCCESS, "DEFLATE decompression status");
    CHECK(actual == input_size, "DEFLATE decompressed length");
    CHECK(actual == input_size && memcmp(decoded, input, input_size) == 0,
          "DEFLATE round-trip bytes");
    free(compressed);

    bound = libdeflate_zlib_compress_bound(compressor, input_size);
    CHECK(bound > 0, "zlib compression bound");
    compressed = bound ? malloc(bound) : NULL;
    CHECK(compressed != NULL, "allocate zlib output");
    if (!compressed)
        goto done;
    compressed_size = libdeflate_zlib_compress(compressor, input, input_size, compressed, bound);
    CHECK(compressed_size > 0, "zlib compression");
    actual = 0;
    result = libdeflate_zlib_decompress(decompressor, compressed, compressed_size,
                                        decoded, sizeof(decoded), &actual);
    CHECK(result == LIBDEFLATE_SUCCESS, "zlib decompression status");
    CHECK(actual == input_size, "zlib decompressed length");
    CHECK(actual == input_size && memcmp(decoded, input, input_size) == 0,
          "zlib round-trip bytes");
    free(compressed);

    bound = libdeflate_gzip_compress_bound(compressor, input_size);
    CHECK(bound > 0, "gzip compression bound");
    compressed = bound ? malloc(bound) : NULL;
    CHECK(compressed != NULL, "allocate gzip output");
    if (!compressed)
        goto done;
    compressed_size = libdeflate_gzip_compress(compressor, input, input_size, compressed, bound);
    CHECK(compressed_size > 0, "gzip compression");
    actual = 0;
    result = libdeflate_gzip_decompress(decompressor, compressed, compressed_size,
                                        decoded, sizeof(decoded), &actual);
    CHECK(result == LIBDEFLATE_SUCCESS, "gzip decompression status");
    CHECK(actual == input_size, "gzip decompressed length");
    CHECK(actual == input_size && memcmp(decoded, input, input_size) == 0,
          "gzip round-trip bytes");
    free(compressed);

    actual = 0;
    result = libdeflate_deflate_decompress(decompressor, "invalid", 7,
                                           decoded, sizeof(decoded), &actual);
    CHECK(result != LIBDEFLATE_SUCCESS, "reject malformed DEFLATE data");

done:
    if (compressor)
        libdeflate_free_compressor(compressor);
    if (decompressor)
        libdeflate_free_decompressor(decompressor);
    printf("Consumer checks: %u passed, %u failed\n", checks - failures, failures);
    return failures ? 1 : 0;
}
