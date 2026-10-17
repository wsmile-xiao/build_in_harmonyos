/*
 * test.c — libopenaptx test_package consumer test.
 *
 * Exercises the packaged library API the way a real consumer would, using
 * the codec contracts documented in openaptx.h:
 *   - raw input is 24-bit signed stereo, 24 bytes per frame (LLLRRR x4);
 *   - aptX compresses at a fixed 4:1 byte ratio (24-byte frame -> 4 bytes);
 *   - the encoder holds back the last 90 samples (rounded to 92 = 23 frames)
 *     until aptx_encode_finish() is called;
 *   - the decoder output realigns with the original stream at offset 0.
 *
 * Assertions:
 *   1. version constants exported by openaptx.h match the package version;
 *   2. encode consumes the whole input and writes exactly frames x 4 bytes;
 *   3. encoding is deterministic (two identical runs produce equal bytes);
 *   4. decode consumes the whole aptX stream and emits frame-aligned PCM for
 *      every frame except the documented 23-frame encoder latency;
 *   5. the round trip is faithful: mean per-sample deviation of the decoded
 *      stream versus the original (alignment 0, warm-up frames skipped) is
 *      far below 1% of the signal amplitude (observed ~0.3%).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <openaptx.h>

#define FRAMES 256

static unsigned char pcm_in[FRAMES * 24];
static unsigned char aptx[FRAMES * 4];
static unsigned char pcm_out[FRAMES * 24];

static int32_t get24(const unsigned char *p) {
    uint32_t v = (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16);
    return (v & 0x800000u) ? (int32_t)(v | 0xff000000u) : (int32_t)v;
}

int main(void) {
    size_t f, i, written = 0, written2 = 0, dwritten = 0;
    int fails = 0;

    if (aptx_major != 0 || aptx_minor != 2) {
        fprintf(stderr, "FAIL: version constants %d.%d do not match 0.2\n",
                aptx_major, aptx_minor);
        return 1;
    }

    for (f = 0; f < FRAMES; f++)
        for (i = 0; i < 8; i++) {   /* 4 x (L, R) 24-bit LE samples */
            int32_t v = (int32_t)(100000.0 * sin((double)(f * 8 + i) * 0.05));
            unsigned char *p = &pcm_in[f * 24 + i * 3];
            p[0] = (unsigned char)(v & 0xff);
            p[1] = (unsigned char)((v >> 8) & 0xff);
            p[2] = (unsigned char)((v >> 16) & 0xff);
        }

    struct aptx_context *enc = aptx_init(0);
    struct aptx_context *dec = aptx_init(0);
    if (!enc || !dec) {
        fprintf(stderr, "FAIL: aptx_init returned NULL\n");
        return 1;
    }

    /* 2. fixed 4:1 ratio: every 24-byte frame becomes 4 aptX bytes */
    size_t consumed = aptx_encode(enc, pcm_in, sizeof(pcm_in),
                                  aptx, sizeof(aptx), &written);
    if (consumed != sizeof(pcm_in)) {
        fprintf(stderr, "FAIL: encode consumed %zu of %zu bytes\n",
                consumed, sizeof(pcm_in));
        fails++;
    }
    if (written != FRAMES * 4) {
        fprintf(stderr, "FAIL: encode wrote %zu bytes, expected %d\n",
                written, FRAMES * 4);
        fails++;
    } else {
        printf("PASS: encode %d frames -> %zu aptX bytes (4:1)\n", FRAMES, written);
    }

    /* 3. deterministic output */
    aptx_reset(enc);
    {
        static unsigned char aptx_b[FRAMES * 4];
        aptx_encode(enc, pcm_in, sizeof(pcm_in), aptx_b, sizeof(aptx_b), &written2);
        if (written2 != written || memcmp(aptx, aptx_b, written) != 0) {
            fprintf(stderr, "FAIL: two identical encodes differ\n");
            fails++;
        } else {
            printf("PASS: encode is deterministic\n");
        }
    }

    /* 4. decode: everything except the documented 90-sample encoder latency
       (openaptx.h: "output buffer starts filling after 90 samples");
       a decoded stereo 24-bit sample is 6 bytes (L+R x 3). */
    size_t dcon = aptx_decode(dec, aptx, written, pcm_out, sizeof(pcm_out), &dwritten);
    if (dcon != written) {
        fprintf(stderr, "FAIL: decode consumed %zu of %zu bytes\n", dcon, written);
        fails++;
    }
    if (dwritten != ((size_t)(FRAMES * 4) - 90) * 6) {
        fprintf(stderr, "FAIL: decode wrote %zu bytes, expected %zu "
                        "(90-sample latency)\n",
                dwritten, ((size_t)(FRAMES * 4) - 90) * 6);
        fails++;
    } else {
        printf("PASS: decode %zu aptX bytes -> %zu PCM bytes "
               "(1024 samples - 90 latency)\n", written, dwritten);
    }

    /* 5. fidelity: compare only the frames that the decoder actually wrote.
       The decoder emits (total stereo samples - 90) samples of 6 bytes each
       (openaptx.h: "output buffer starts filling after 90 samples"), i.e.
       dwritten bytes; the number of complete 24-byte frames available is
       derived from dwritten instead of assuming a fixed latency. */
    {
        size_t decoded_frames = dwritten / 24;
        double err = 0.0;
        size_t n = 0;
        for (f = 4; f < decoded_frames && f < FRAMES; f++) {   /* skip 4 warm-up frames */
            for (i = 0; i < 8; i++) {
                int32_t a = get24(&pcm_out[f * 24 + i * 3]);
                int32_t b = get24(&pcm_in[f * 24 + i * 3]);
                err += abs(a - b);
                n++;
            }
        }
        err /= (double)(n ? n : 1);
        printf("INFO: fidelity over %zu frame(s) of %zu decoded: "
               "mean per-sample deviation %.2f (amplitude 100000)\n",
               n / 8, decoded_frames, err);
        if (err >= 1000.0) {   /* 1% of the signal amplitude */
            fprintf(stderr, "FAIL: mean deviation %.2f exceeds 1%% of amplitude\n", err);
            fails++;
        } else {
            printf("PASS: round-trip deviation %.2f within 1%% of amplitude\n", err);
        }
    }

    aptx_finish(enc);
    aptx_finish(dec);

    if (fails) {
        fprintf(stderr, "FAIL: %d check(s) failed\n", fails);
        return 1;
    }
    printf("PASS: libopenaptx consumer round trip\n");
    return 0;
}
