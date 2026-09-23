/* Installed-package consumer: libaec streaming round-trip.
 *
 * Encodes synthetic correlated 8-bit signed samples with aec_encode and
 * restores them with aec_decode, following the upstream README example.
 * Prints one CHECK line per assertion and a final LIBSZ_TEST verdict;
 * returns non-zero on any failure so the harness cannot mistake silence
 * for success.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "libaec.h"

#define SAMPLE_COUNT 2048

static int check(int id, int total, int ok, const char *what)
{
    printf("CHECK aec-roundtrip %d/%d %s: %s\n",
           id, total, what, ok ? "ok" : "FAIL");
    return ok ? 0 : 1;
}

int main(void)
{
    static signed char source[SAMPLE_COUNT];
    static unsigned char packed[SAMPLE_COUNT * 2];
    static signed char restored[SAMPLE_COUNT + 64];
    struct aec_stream strm;
    size_t i;
    int failures = 0;

    for (i = 0; i < SAMPLE_COUNT; ++i) {
        source[i] = (signed char)(((i / 16) % 32) - 16);
    }

    strm.bits_per_sample = 8;
    strm.block_size = 16;
    strm.rsi = 128;
    strm.flags = AEC_DATA_SIGNED | AEC_DATA_PREPROCESS;
    strm.next_in = (unsigned char *)source;
    strm.avail_in = sizeof(source);
    strm.next_out = packed;
    strm.avail_out = sizeof(packed);

    failures += check(1, 5, aec_encode_init(&strm) == AEC_OK,
                      "encode_init returns AEC_OK");
    failures += check(2, 5, aec_encode(&strm, AEC_FLUSH) == AEC_OK,
                      "encode returns AEC_OK");
    failures += check(3, 5, strm.total_out > 0,
                      "encoder produced output");
    {
        size_t encoded_len = strm.total_out;
        aec_encode_end(&strm);

        strm.bits_per_sample = 8;
        strm.block_size = 16;
        strm.rsi = 128;
        strm.flags = AEC_DATA_SIGNED | AEC_DATA_PREPROCESS;
        strm.next_in = packed;
        strm.avail_in = encoded_len;
        strm.next_out = (unsigned char *)restored;
        strm.avail_out = sizeof(restored);

        failures += check(4, 5, aec_decode_init(&strm) == AEC_OK &&
                          aec_decode(&strm, AEC_FLUSH) == AEC_OK,
                          "decode returns AEC_OK");
        failures += check(5, 5, strm.total_out >= sizeof(source) &&
                          memcmp(source, restored, sizeof(source)) == 0,
                          "round-trip prefix matches input");
        aec_decode_end(&strm);
    }

    if (failures == 0) {
        printf("LIBSZ_TEST aec-roundtrip PASS\n");
        return 0;
    }
    printf("LIBSZ_TEST aec-roundtrip FAIL (%d failed checks)\n", failures);
    return 1;
}
