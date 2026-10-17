/* Consumer test for libamrnb 11.0.0.0.
 *
 * Exercises the 3GPP TS 26.104 reference interface exposed by the wrapper
 * (default GP3 packed storage format): encode in all 8 AMR-NB modes with
 * exact frame-size checks, DTX/SID encoding, and a multi-frame MR122
 * round-trip whose decoded sine peak is checked after the decoder has
 * converged (the decoder needs a couple of frames from reset state).
 */
#include <stdio.h>
#include <math.h>
#include <string.h>

#include <amrnb/interf_enc.h>   /* pulls in sp_enc.h: enum Mode */
#include <amrnb/interf_dec.h>

#define FRAMESZ 160             /* 20 ms at 8 kHz */

static int failures = 0;

#define CHECK(cond, msg)                                                \
    do {                                                                \
        if (!(cond)) {                                                  \
            fprintf(stderr, "FAIL: %s\n", msg);                         \
            failures++;                                                 \
        }                                                               \
    } while (0)

int main(void)
{
    int i, mode_idx, fr, n;
    short speech[FRAMESZ];
    unsigned char buf[32];
    short synth[FRAMESZ];
    long peak;
    void *enc, *dec;
    const enum Mode modes[8] = {
        MR475, MR515, MR59, MR67, MR74, MR795, MR102, MR122
    };
    /* GP3 storage-format frame sizes observed on the reference codec:
     * 1 TOC/header byte + RFC 4867 payload per mode */
    const int expect_bytes[8] = { 13, 14, 16, 18, 20, 21, 27, 32 };

    /* --- one frame of 1 kHz sine, amplitude 8000 (2 full cycles) --- */
    for (i = 0; i < FRAMESZ; i++) {
        speech[i] = (short)(8000.0 * sin(2.0 * 3.14159265358979 * 1000.0 * i / 8000.0));
    }

    /* --- encoder init --- */
    enc = Encoder_Interface_init(0);
    CHECK(enc != NULL, "Encoder_Interface_init returned NULL");

    /* --- encode one frame in every mode, exact GP3 sizes --- */
    for (mode_idx = 0; mode_idx < 8; mode_idx++) {
        n = Encoder_Interface_Encode(enc, modes[mode_idx], speech, buf, 0);
        CHECK(n == expect_bytes[mode_idx],
              "Encoder_Interface_Encode frame size differs from GP3 storage format");
        printf("mode %d: %d bytes\n", (int)modes[mode_idx], n);
    }

    /* --- DTX encoder produces SID frames on silence --- */
    {
        void *enc_dtx = Encoder_Interface_init(1);
        short silence[FRAMESZ] = {0};
        CHECK(enc_dtx != NULL, "Encoder_Interface_init(dtx=1) returned NULL");
        n = Encoder_Interface_Encode(enc_dtx, MR122, silence, buf, 0);
        CHECK(n > 0 && n <= 32, "DTX encode produced out-of-range frame size");
        Encoder_Interface_exit(enc_dtx);
    }

    /* --- decoder init --- */
    dec = Decoder_Interface_init();
    CHECK(dec != NULL, "Decoder_Interface_init returned NULL");

    /* --- multi-frame MR122 round-trip: the decoder needs a few frames
     *     to converge from its reset state before the output tracks the
     *     input amplitude, so only measure the peak from frame 3 on --- */
    peak = 0;
    for (fr = 0; fr < 6; fr++) {
        n = Encoder_Interface_Encode(enc, MR122, speech, buf, 0);
        CHECK(n == expect_bytes[7], "MR122 round-trip frame encode size mismatch");
        Decoder_Interface_Decode(dec, buf, synth, 0);
        if (fr >= 2) {
            for (i = 0; i < FRAMESZ; i++) {
                long a = synth[i] < 0 ? -(long)synth[i] : (long)synth[i];
                if (a > peak)
                    peak = a;
            }
        }
    }
    Encoder_Interface_exit(enc);
    Decoder_Interface_exit(dec);

    /* A clean 1 kHz sine at 12.2 kbit/s must survive recognisably:
     * require at least half the input amplitude somewhere after warm-up. */
    CHECK(peak >= 4000, "decoded sine peak too low (codec round-trip broken)");

    if (failures) {
        fprintf(stderr, "%d assertion(s) failed\n", failures);
        return 1;
    }
    printf("libamrnb round-trip OK (peak=%ld)\n", peak);
    return 0;
}
