/* HarmonyOS-specific consumer test for the OHOS allocator adaptation. */
#include <lzham.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if !defined(__OHOS__)
#error "test_lzham_ohos must be compiled for OpenHarmony"
#endif

#if !defined(__linux__)
#error "the OHOS build must expose the Linux-compatible LZHAM path"
#endif

static int round_trip(size_t input_len)
{
    unsigned char *input = NULL;
    unsigned char *compressed = NULL;
    unsigned char *decompressed = NULL;
    lzham_z_ulong compressed_len;
    lzham_z_ulong decompressed_len;
    size_t i;
    int rc;

    input = (unsigned char *)malloc(input_len);
    compressed_len = lzham_z_compressBound((lzham_z_ulong)input_len);
    compressed = (unsigned char *)malloc((size_t)compressed_len);
    decompressed = (unsigned char *)malloc(input_len);
    if (!input || !compressed || !decompressed)
        goto failure;

    for (i = 0; i < input_len; ++i)
        input[i] = (unsigned char)((i * 37U) ^ (i >> 3));

    rc = lzham_z_compress(compressed, &compressed_len, input,
                          (lzham_z_ulong)input_len);
    if (rc != LZHAM_Z_OK)
        goto failure;

    decompressed_len = (lzham_z_ulong)input_len;
    rc = lzham_z_uncompress(decompressed, &decompressed_len, compressed,
                            compressed_len);
    if (rc != LZHAM_Z_OK || decompressed_len != (lzham_z_ulong)input_len ||
        memcmp(input, decompressed, input_len) != 0)
        goto failure;

    free(input);
    free(compressed);
    free(decompressed);
    return 0;

failure:
    free(input);
    free(compressed);
    free(decompressed);
    return 1;
}

int main(void)
{
    /* These sizes straddle the 16-byte alignment boundary used by LZHAM. */
    static const size_t sizes[] = {1U, 15U, 16U, 17U, 31U, 32U, 33U,
                                   255U, 4096U, 65536U};
    size_t i;

    for (i = 0; i < sizeof(sizes) / sizeof(sizes[0]); ++i) {
        if (round_trip(sizes[i]) != 0) {
            fprintf(stderr, "LZHAM OHOS alignment case failed: %lu bytes\n",
                    (unsigned long)sizes[i]);
            return 1;
        }
    }

    printf("LZHAM OHOS alignment-path test: %lu/%lu cases passed\n",
           (unsigned long)(sizeof(sizes) / sizeof(sizes[0])),
           (unsigned long)(sizeof(sizes) / sizeof(sizes[0])));
    return 0;
}
