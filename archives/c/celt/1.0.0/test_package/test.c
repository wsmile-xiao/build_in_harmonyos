/*
 * test.c — CELT installed-package smoke test.
 *
 * Exercises celt_mode_create / celt_encoder_create / celt_decoder_create /
 * celt_encode / celt_decode round-trip on a buffer of silence, then
 * verifies error-string lookup.  All operations must succeed for the
 * test to return 0.
 */

#include <celt/celt.h>
#include <stdio.h>
#include <string.h>

#define SAMPLE_RATE  48000
#define FRAME_SIZE   960      /* 20 ms at 48 kHz */
#define CHANNELS     1
#define MAX_PACKET   1275

int main(void)
{
    int error = CELT_OK;
    int result = 0;
    CELTMode *mode = NULL;
    CELTEncoder *enc = NULL;
    CELTDecoder *dec = NULL;
    celt_int16 pcm_in[FRAME_SIZE * CHANNELS];
    celt_int16 pcm_out[FRAME_SIZE * CHANNELS];
    unsigned char data[MAX_PACKET];
    int len;

    memset(pcm_in, 0, sizeof(pcm_in));

    /* 1. Create mode */
    mode = celt_mode_create(SAMPLE_RATE, FRAME_SIZE, &error);
    if (!mode || error != CELT_OK) {
        fprintf(stderr, "FAIL: celt_mode_create returned %d\n", error);
        result = 1;
        goto cleanup;
    }

    /* 2. Create encoder */
    enc = celt_encoder_create_custom(mode, CHANNELS, &error);
    if (!enc || error != CELT_OK) {
        fprintf(stderr, "FAIL: celt_encoder_create_custom returned %d\n", error);
        result = 2;
        goto cleanup;
    }

    /* 3. Create decoder */
    dec = celt_decoder_create_custom(mode, CHANNELS, &error);
    if (!dec || error != CELT_OK) {
        fprintf(stderr, "FAIL: celt_decoder_create_custom returned %d\n", error);
        result = 3;
        goto cleanup;
    }

    /* 4. Encode a frame of silence */
    len = celt_encode(enc, pcm_in, FRAME_SIZE, data, MAX_PACKET);
    if (len <= 0) {
        fprintf(stderr, "FAIL: celt_encode returned %d (%s)\n",
                len, celt_strerror(len));
        result = 4;
        goto cleanup;
    }

    /* 5. Decode the encoded frame */
    error = celt_decode(dec, data, len, pcm_out, FRAME_SIZE);
    if (error < 0) {
        fprintf(stderr, "FAIL: celt_decode returned %d (%s)\n",
                error, celt_strerror(error));
        result = 5;
        goto cleanup;
    }

    /* 6. Verify error-string lookup works */
    if (strcmp(celt_strerror(CELT_OK), "success") != 0) {
        fprintf(stderr, "FAIL: celt_strerror(CELT_OK) = \"%s\"\n",
                celt_strerror(CELT_OK));
        result = 6;
        goto cleanup;
    }

    puts("celt installed-package encode/decode round-trip passed");

cleanup:
    if (dec)  celt_decoder_destroy(dec);
    if (enc)  celt_encoder_destroy(enc);
    if (mode) celt_mode_destroy(mode);
    return result;
}
