/* Consumer test: exercise the public zlib-style LZHAM API end to end. */
#include <lzham.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define INPUT_LEN (64U * 1024U)

static int fail(const char *message, int code)
{
    fprintf(stderr, "LZHAM test failure: %s (%d)\n", message, code);
    return 1;
}

int main(void)
{
    unsigned char *input = NULL;
    unsigned char *compressed = NULL;
    unsigned char *decompressed = NULL;
    lzham_z_ulong compressed_len;
    lzham_z_ulong decompressed_len;
    int rc;
    size_t i;

    if (lzham_get_version() != LZHAM_DLL_VERSION)
        return fail("version mismatch", 0);

    input = (unsigned char *)malloc(INPUT_LEN);
    compressed_len = lzham_z_compressBound((lzham_z_ulong)INPUT_LEN);
    compressed = (unsigned char *)malloc((size_t)compressed_len);
    decompressed = (unsigned char *)malloc(INPUT_LEN);
    if (!input || !compressed || !decompressed) {
        free(input);
        free(compressed);
        free(decompressed);
        return fail("allocation failed", 0);
    }

    for (i = 0; i < INPUT_LEN; ++i)
        input[i] = (unsigned char)((i % 251U) ^ ((i / 251U) & 0x0FU));

    rc = lzham_z_compress(compressed, &compressed_len, input,
                          (lzham_z_ulong)INPUT_LEN);
    if (rc != LZHAM_Z_OK) {
        free(input);
        free(compressed);
        free(decompressed);
        return fail("compression failed", rc);
    }

    decompressed_len = (lzham_z_ulong)INPUT_LEN;
    rc = lzham_z_uncompress(decompressed, &decompressed_len, compressed,
                            compressed_len);
    if (rc != LZHAM_Z_OK) {
        free(input);
        free(compressed);
        free(decompressed);
        return fail("decompression failed", rc);
    }

    if (decompressed_len != (lzham_z_ulong)INPUT_LEN ||
        memcmp(input, decompressed, INPUT_LEN) != 0) {
        free(input);
        free(compressed);
        free(decompressed);
        return fail("round-trip mismatch", 0);
    }

    printf("LZHAM round-trip OK: %u -> %lu bytes\n", INPUT_LEN,
           (unsigned long)compressed_len);
    free(input);
    free(compressed);
    free(decompressed);
    return 0;
}
