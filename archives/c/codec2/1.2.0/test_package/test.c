/* test_package/test.c — L1 consumer test for codec2
 * Calls codec2 API to encode/decode a voice frame and verify round-trip.
 */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "codec2/codec2.h"

int main(void) {
    int mode = CODEC2_MODE_3200;
    struct CODEC2 *c2 = codec2_create(mode);
    if (c2 == NULL) {
        fprintf(stderr, "FAIL: codec2_create returned NULL\n");
        return 1;
    }

    int nsamp = codec2_samples_per_frame(c2);
    int nbits = codec2_bits_per_frame(c2);
    printf("codec2 mode=%d samples=%d bits=%d\n", mode, nsamp, nbits);

    if (nsamp <= 0 || nbits <= 0) {
        fprintf(stderr, "FAIL: invalid frame dimensions\n");
        codec2_destroy(c2);
        return 1;
    }

    /* Generate a simple test signal (sine-like) */
    short *speech_in = (short *)malloc(nsamp * sizeof(short));
    if (speech_in == NULL) {
        fprintf(stderr, "FAIL: out of memory\n");
        codec2_destroy(c2);
        return 1;
    }
    for (int i = 0; i < nsamp; i++) {
        speech_in[i] = (short)(32767.0 * 0.5 * sin(2.0 * 3.14159 * 400.0 * i / 8000.0));
    }

    /* Encode */
    int nbytes = (nbits + 7) / 8;
    unsigned char *encoded = (unsigned char *)calloc(nbytes, sizeof(unsigned char));
    if (encoded == NULL) {
        fprintf(stderr, "FAIL: out of memory for encoded\n");
        free(speech_in);
        codec2_destroy(c2);
        return 1;
    }
    codec2_encode(c2, encoded, speech_in);

    /* Decode */
    short *speech_out = (short *)malloc(nsamp * sizeof(short));
    if (speech_out == NULL) {
        fprintf(stderr, "FAIL: out of memory for decoded\n");
        free(speech_in);
        free(encoded);
        codec2_destroy(c2);
        return 1;
    }
    codec2_decode(c2, speech_out, encoded);

    /* Verify output is non-zero (decode produced something) */
    int has_signal = 0;
    for (int i = 0; i < nsamp; i++) {
        if (speech_out[i] != 0) {
            has_signal = 1;
            break;
        }
    }

    printf("encode/decode round-trip: %s\n", has_signal ? "OK" : "FAIL (all zeros)");

    free(speech_in);
    free(encoded);
    free(speech_out);
    codec2_destroy(c2);

    if (!has_signal) {
        fprintf(stderr, "FAIL: decoded output is all zeros\n");
        return 1;
    }

    printf("test codec2 1.2.0: PASS\n");
    return 0;
}
