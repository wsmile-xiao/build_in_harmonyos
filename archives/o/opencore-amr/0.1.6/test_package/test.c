/* Test program for opencore-amr: encode and decode AMR-NB, decode AMR-WB */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <opencore-amrnb/interf_enc.h>
#include <opencore-amrnb/interf_dec.h>
#include <opencore-amrwb/dec_if.h>

int main(void) {
    /* --- AMR-NB encode test --- */
    void *enc_state = Encoder_Interface_init(0);
    if (!enc_state) {
        fprintf(stderr, "FAIL: Encoder_Interface_init returned NULL\n");
        return 1;
    }

    /* 160 samples (20ms at 8kHz) of silence for AMR-NB */
    short speech[160] = {0};
    unsigned char encoded[32];
    int n = Encoder_Interface_Encode(enc_state, MR122, speech, encoded, 0);
    if (n <= 0) {
        fprintf(stderr, "FAIL: Encoder_Interface_Encode returned %d\n", n);
        Encoder_Interface_exit(enc_state);
        return 1;
    }
    Encoder_Interface_exit(enc_state);

    /* --- AMR-NB decode test --- */
    void *dec_state = Decoder_Interface_init();
    if (!dec_state) {
        fprintf(stderr, "FAIL: Decoder_Interface_init returned NULL\n");
        return 1;
    }

    short decoded[160];
    Decoder_Interface_Decode(dec_state, encoded, decoded, 0);
    Decoder_Interface_exit(dec_state);

    /* --- AMR-WB decode test --- */
    void *wb_dec_state = D_IF_init();
    if (!wb_dec_state) {
        fprintf(stderr, "FAIL: D_IF_init returned NULL\n");
        return 1;
    }

    /* Minimal AMR-WB frame (47 bytes for 23.85 kbps mode) */
    unsigned char wb_frame[47] = {0};
    /* Set mode bits to 23.85 kbps (111 in bits 0-2) */
    wb_frame[0] = 0xE0;
    short wb_synth[320];
    D_IF_decode(wb_dec_state, wb_frame, wb_synth, 0);
    D_IF_exit(wb_dec_state);

    printf("opencore-amr 0.1.6: AMR-NB encode (%d bytes) + decode OK, AMR-WB decode OK\n", n);
    return 0;
}
