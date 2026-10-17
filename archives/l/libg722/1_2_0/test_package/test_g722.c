#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "g722.h"
#include "g722_encoder.h"
#include "g722_decoder.h"

#define N_SAMPLES 160
#define CHECK(name, cond) do { \
    if (cond) { printf("CHECK-OK: %s\n", name); passed++; } \
    else { printf("CHECK-FAIL: %s\n", name); } \
    total++; \
} while (0)

static void fill_pcm(int16_t *pcm, int n) {
    for (int i = 0; i < n; i++) {
        /* Deterministic 8 kHz-ish sine sweep, fits in int16. */
        int v = (i * 997) % 65536 - 32768;
        pcm[i] = (int16_t)(v / 4);
    }
}

int main(void) {
    int total = 0;
    int passed = 0;

    int16_t pcm[N_SAMPLES];
    uint8_t coded[N_SAMPLES];
    int16_t decoded[N_SAMPLES];
    fill_pcm(pcm, N_SAMPLES);

    /* 1. encoder context lifecycle + encode at 64k */
    G722_ENC_CTX *enc = g722_encoder_new(64000, G722_DEFAULT);
    CHECK("encoder_new_64k", enc != NULL);
    int nbytes = 0;
    if (enc != NULL) {
        nbytes = g722_encode(enc, pcm, N_SAMPLES, coded);
    }
    CHECK("encode_64k_len", nbytes == N_SAMPLES / 2);
    CHECK("encode_output_nontrivial", nbytes > 0 && memcmp(pcm, coded, 8) != 0);

    /* 2. decoder context lifecycle + decode round-trip */
    G722_DEC_CTX *dec = g722_decoder_new(64000, G722_DEFAULT);
    CHECK("decoder_new_64k", dec != NULL);
    int ndec = 0;
    if (dec != NULL && nbytes > 0) {
        ndec = g722_decode(dec, coded, nbytes, decoded);
    }
    CHECK("decode_roundtrip_len", ndec == N_SAMPLES);
    if (enc != NULL) {
        CHECK("encoder_destroy", g722_encoder_destroy(enc) == 0);
    } else {
        CHECK("encoder_destroy", 0);
    }
    if (dec != NULL) {
        CHECK("decoder_destroy", g722_decoder_destroy(dec) == 0);
    } else {
        CHECK("decoder_destroy", 0);
    }

    /* 3. all three bit rates encode without error */
    {
        int ok = 1;
        int rates[3] = {64000, 56000, 48000};
        for (int r = 0; r < 3; r++) {
            G722_ENC_CTX *e = g722_encoder_new(rates[r], G722_DEFAULT);
            if (e == NULL) { ok = 0; break; }
            int nb = g722_encode(e, pcm, N_SAMPLES, coded);
            g722_encoder_destroy(e);
            if (nb <= 0) { ok = 0; break; }
        }
        CHECK("encode_all_bitrates", ok);
    }

    /* 4. 8 kHz narrowband interop mode round-trip */
    {
        G722_ENC_CTX *e8 = g722_encoder_new(64000, G722_SAMPLE_RATE_8000);
        G722_DEC_CTX *d8 = g722_decoder_new(64000, G722_SAMPLE_RATE_8000);
        int ok = (e8 != NULL && d8 != NULL);
        if (ok) {
            int nb = g722_encode(e8, pcm, N_SAMPLES, coded);
            int nd = g722_decode(d8, coded, nb, decoded);
            ok = (nb > 0 && nd > 0);
        }
        if (e8 != NULL) { g722_encoder_destroy(e8); }
        if (d8 != NULL) { g722_decoder_destroy(d8); }
        CHECK("narrowband_8k_roundtrip", ok);
    }

    printf("SUMMARY: %d/%d checks passed\n", passed, total);
    return (passed == total) ? 0 : 1;
}
