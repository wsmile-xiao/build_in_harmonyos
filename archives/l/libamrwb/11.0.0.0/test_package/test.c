/* Consumer test for libamrwb 11.0.0.0.
 *
 * Exercises the 3GPP TS 26.204 reference interface exposed by the wrapper
 * (default GP3 packed storage format): encode in all 9 AMR-WB modes with
 * exact frame-size checks (RFC 3267 storage format, 1-byte TOC + payload),
 * DTX/SID encoding on silence, and a multi-frame mode-8 round-trip whose
 * decoded sine peak is checked after the decoder has converged (the
 * decoder needs a couple of frames from reset state).
 */
#include <stdio.h>
#include <math.h>
#include <string.h>

#include <amrwb/enc_if.h>    /* E_IF_init / E_IF_encode / E_IF_exit */
#include <amrwb/dec_if.h>    /* D_IF_init / D_IF_decode / D_IF_exit */
#include <amrwb/typedef.h>   /* Word16, UWord8, Word32, NB_SERIAL_MAX */

#define FRAMESZ 320             /* 20 ms at 16 kHz (L_FRAME16k) */

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
    Word16 speech[FRAMESZ];
    UWord8 serial[NB_SERIAL_MAX];       /* max serial size 61 */
    Word16 synth[FRAMESZ];
    long peak;
    void *enc, *dec;
    /* RFC 3267 AMR-WB file-storage frame sizes per mode 0..8:
     * 1 TOC/header byte + RFC 4867 payload size */
    const int expect_bytes[9] = { 18, 24, 33, 37, 41, 47, 51, 59, 61 };

    /* --- one frame of 1 kHz sine, amplitude 8000 (2 full cycles) --- */
    for (i = 0; i < FRAMESZ; i++) {
        speech[i] = (Word16)(8000.0 * sin(2.0 * 3.14159265358979 * 1000.0 * i / 16000.0));
    }

    /* --- encoder init --- */
    enc = E_IF_init();
    CHECK(enc != NULL, "E_IF_init returned NULL");

    /* --- encode one frame in every mode, exact RFC 3267 sizes --- */
    for (mode_idx = 0; mode_idx < 9; mode_idx++) {
        n = E_IF_encode(enc, (Word16)mode_idx, speech, serial, 0);
        CHECK(n == expect_bytes[mode_idx],
              "E_IF_encode frame size differs from RFC 3267 storage format");
        printf("mode %d: %d bytes\n", mode_idx, n);
    }

    /* --- DTX encoder produces SID frames on silence --- */
    {
        void *enc_dtx = E_IF_init();
        Word16 silence[FRAMESZ] = {0};
        CHECK(enc_dtx != NULL, "E_IF_init (DTX) returned NULL");
        n = E_IF_encode(enc_dtx, 8, silence, serial, 1);
        CHECK(n > 0 && n <= NB_SERIAL_MAX,
              "DTX encode produced out-of-range frame size");
        printf("dtx: %d bytes\n", n);
        E_IF_exit(enc_dtx);
    }

    /* --- decoder init --- */
    dec = D_IF_init();
    CHECK(dec != NULL, "D_IF_init returned NULL");

    /* --- multi-frame mode 8 round-trip: the decoder needs a few frames
     *     to converge from its reset state before the output tracks the
     *     input amplitude, so only measure the peak from frame 3 on --- */
    peak = 0;
    for (fr = 0; fr < 6; fr++) {
        n = E_IF_encode(enc, 8, speech, serial, 0);
        CHECK(n == expect_bytes[8], "mode 8 round-trip frame encode size mismatch");
        D_IF_decode(dec, serial, synth, 0);
        if (fr >= 2) {
            for (i = 0; i < FRAMESZ; i++) {
                long a = synth[i] < 0 ? -(long)synth[i] : (long)synth[i];
                if (a > peak)
                    peak = a;
            }
        }
    }
    E_IF_exit(enc);
    D_IF_exit(dec);

    /* A clean 1 kHz sine at 23.85 kbit/s must survive recognisably:
     * require at least half the input amplitude somewhere after warm-up. */
    CHECK(peak >= 4000, "decoded sine peak too low (codec round-trip broken)");

    if (failures) {
        fprintf(stderr, "%d assertion(s) failed\n", failures);
        return 1;
    }
    printf("libamrwb round-trip OK (peak=%ld)\n", peak);
    return 0;
}
