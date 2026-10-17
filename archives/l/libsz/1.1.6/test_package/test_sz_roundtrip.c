/* Installed-package consumer: libsz (SZIP-compatible) round-trip.
 *
 * Compresses synthetic low-entropy 8-bit samples with
 * SZ_BufftoBuffCompress and restores them with SZ_BufftoBuffDecompress.
 * Prints one CHECK line per assertion and a final LIBSZ_TEST verdict;
 * returns non-zero on any failure so the harness cannot mistake silence
 * for success.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "szlib.h"

#define SAMPLE_COUNT 4096

static int check(int id, int total, int ok, const char *what)
{
    printf("CHECK sz-roundtrip %d/%d %s: %s\n",
           id, total, what, ok ? "ok" : "FAIL");
    return ok ? 0 : 1;
}

int main(void)
{
    static unsigned char source[SAMPLE_COUNT];
    static unsigned char packed[SAMPLE_COUNT * 2];
    static unsigned char restored[SAMPLE_COUNT];
    SZ_com_t params;
    size_t packed_len = sizeof(packed);
    size_t restored_len = sizeof(restored);
    size_t i;
    int failures = 0;
    int status;

    for (i = 0; i < SAMPLE_COUNT; ++i) {
        source[i] = (unsigned char)((i / 32) % 8);
    }

    params.options_mask = SZ_RAW_OPTION_MASK | SZ_NN_OPTION_MASK;
    params.bits_per_pixel = 8;
    params.pixels_per_block = 16;
    params.pixels_per_scanline = 1024;

    status = SZ_BufftoBuffCompress(packed, &packed_len,
                                   source, sizeof(source), &params);
    failures += check(1, 5, status == SZ_OK, "compress returns SZ_OK");
    failures += check(2, 5, packed_len > 0 && packed_len < sizeof(source),
                      "compressed output is smaller than input");

    status = SZ_BufftoBuffDecompress(restored, &restored_len,
                                     packed, packed_len, &params);
    failures += check(3, 5, status == SZ_OK, "decompress returns SZ_OK");
    failures += check(4, 5, restored_len == sizeof(source),
                      "decompressed length matches input");
    failures += check(5, 5, memcmp(source, restored, sizeof(source)) == 0,
                      "round-trip bytes are identical");

    if (failures == 0) {
        printf("LIBSZ_TEST sz-roundtrip PASS\n");
        return 0;
    }
    printf("LIBSZ_TEST sz-roundtrip FAIL (%d failed checks)\n", failures);
    return 1;
}
