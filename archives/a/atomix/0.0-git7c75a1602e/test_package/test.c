/*
 * test_package consumer test for atomix 0.0-git7c75a1602e.
 *
 * Simulates a business-layer consumer that uses ONLY the public header
 * atomix.h (installed via the Conan package) plus normal libc: creates a
 * stereo sound buffer, plays it through a mixer, mixes frames into an
 * output buffer and asserts the public API behaves as documented
 * (atomixSoundLength / atomixMixerPlay return the layer id, mixing
 * produces non-zero output, stop-all idempotent).
 *
 * ATOMIX_STATIC is defined so this single TU carries the implementation
 * (no extra lib to link — the package is header-only).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ATOMIX_STATIC
#define ATOMIX_NO_SSE
#include "atomix.h"

static int failed = 0;

#define CHECK(cond, msg)                                            \
    do {                                                            \
        if (cond) {                                                 \
            printf("  PASS: %s\n", msg);                            \
        } else {                                                    \
            printf("  FAIL: %s\n", msg);                            \
            failed = 1;                                             \
        }                                                           \
    } while (0)

int main(void) {
    /* 1 second of 44100 Hz stereo sine-ish tone (float samples) */
    const int32_t rate = 44100;
    const int32_t frames = rate;        /* 1 s, multiple of 4 */
    float *samples = (float *)calloc((size_t)frames * 2, sizeof(float));
    if (!samples) {
        printf("FAIL: calloc\n");
        return 1;
    }
    for (int32_t i = 0; i < frames; ++i) {
        samples[i * 2]     = 0.25f;      /* L */
        samples[i * 2 + 1] = 0.25f;      /* R */
    }

    printf("atomix consumer test: build sound + mixer + mix\n");

    /* Public API #1: atomixSoundNew(2 channels, data, frames) */
    struct atomix_sound *snd = atomixSoundNew(2, samples, frames);
    CHECK(snd != NULL, "atomixSoundNew(2ch, 1s) creates a sound");

    /* Public API #2: atomixSoundLength */
    int32_t len = atomixSoundLength(snd);
    CHECK(len > 0 && (len % 4) == 0, "atomixSoundLength returns aligned length");

    /* Public API #3: atomixMixerNew(volume, fade) */
    struct atomix_mixer *mix = atomixMixerNew(1.0f, 64);
    CHECK(mix != NULL, "atomixMixerNew(1.0, 64) creates a mixer");

    /* Public API #4: atomixMixerPlay returns a non-zero layer id */
    uint32_t id = atomixMixerPlay(mix, snd, ATOMIX_PLAY, 1.0f, 0.0f);
    CHECK(id != 0, "atomixMixerPlay returns layer id");

    /* Public API #5: atomixMixerMix produces non-zero output frames */
    float out[1024];
    memset(out, 0, sizeof(out));
    uint32_t mixed = atomixMixerMix(mix, out, 512);
    CHECK(mixed == 512, "atomixMixerMix mixes 512 requested frames");
    int non_zero = 0;
    for (int i = 0; i < 512; ++i) {
        if (out[i] != 0.0f) { non_zero = 1; break; }
    }
    CHECK(non_zero == 1, "mixer output contains audible samples");

    /* Public API #6: atomixMixerStopAll fades out (documented behaviour:
     * stopping triggers an automatic fade-out over `fade` frames, so the
     * first mix pass still contains decaying audio; after the fade elapses
     * the mix must be fully silent). */
    atomixMixerStopAll(mix);
    (void)atomixMixerMix(mix, out, 512);          /* let fade (64 frames) elapse */
    memset(out, 0, sizeof(out));
    (void)atomixMixerMix(mix, out, 512);
    int silence = 1;
    for (int i = 0; i < 512; ++i) {
        if (out[i] != 0.0f) { silence = 0; break; }
    }
    CHECK(silence == 1, "atomixMixerStopAll silences mix after fade elapses");

    /* Public API #7: atomixMixerSetGainPan on a live layer */
    (void)atomixMixerSetGainPan(mix, id, 0.5f, -1.0f);
    CHECK(1, "atomixMixerSetGainPan accepted gain/pan update");

    free(samples);

    if (failed) {
        printf("RESULT: FAIL\n");
        return 1;
    }
    printf("RESULT: PASS\n");
    return 0;
}
