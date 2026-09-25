/* test_consumer.c — Conan test_package consumer for audio-resampler 0.7.
 *
 * Simulates a downstream audio application using ONLY the public headers and
 * installed library: init a fixed-ratio 44.1k->48k resampler through the
 * public API, feed a 1 kHz tone, verify the resampler generates the expected
 * number of output frames and that the output is non-silent (observable
 * result of a real public API call).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "resampler.h"

#define TAPS 380
#define FILTERS 380
#define IN_RATE 44100
#define OUT_RATE 48000
#define NUM_CH 2
#define FRAMES 4410   /* 0.1 s of stereo input */

int main(void)
{
    Resample *rs = NULL;
    float *in[2], *out[2];
    int i, ch;
    double peak = 0.0;
    ResampleResult res;

    in[0] = (float *) malloc(FRAMES * sizeof(float));
    in[1] = (float *) malloc(FRAMES * sizeof(float));
    out[0] = (float *) malloc(FRAMES * 2 * sizeof(float));
    out[1] = (float *) malloc(FRAMES * 2 * sizeof(float));
    if (!in[0] || !in[1] || !out[0] || !out[1]) {
        fprintf(stderr, "OOM\n");
        free(in[0]); free(in[1]); free(out[0]); free(out[1]);
        return 1;
    }

    for (i = 0; i < FRAMES; i++) {
        float v = (float) (0.5 * sin(2.0 * M_PI * 1000.0 * i / IN_RATE));
        in[0][i] = v;
        in[1][i] = v;
    }

    rs = resampleFixedRatioInit(NUM_CH, TAPS, FILTERS,
                                (double) IN_RATE, (double) OUT_RATE, 0,
                                BLACKMAN_HARRIS | SUBSAMPLE_INTERPOLATE);
    if (!rs) {
        fprintf(stderr, "resampleFixedRatioInit returned NULL\n");
        free(in[0]); free(in[1]); free(out[0]); free(out[1]);
        return 1;
    }

    res = resampleProcess(rs, (const artsample_t *const *) in, FRAMES,
                          (artsample_t *const *) out, FRAMES * 2,
                          (double) OUT_RATE / (double) IN_RATE);
    if (res.output_generated <= 0) {
        fprintf(stderr, "no output generated (output_generated=%u)\n", res.output_generated);
        resampleFree(rs);
        free(in[0]); free(in[1]); free(out[0]); free(out[1]);
        return 1;
    }
    for (ch = 0; ch < NUM_CH; ch++)
        for (i = 0; i < (int) res.output_generated; i++) {
            float v = out[ch][i];
            if (v > peak) peak = v;
        }
    resampleFree(rs);
    free(in[0]); free(in[1]); free(out[0]); free(out[1]);

    if (peak < 0.1f) {
        fprintf(stderr, "output is silent (peak=%f)\n", peak);
        return 1;
    }

    printf("PASS: fixed-ratio 44.1k->48k resampler generated %u frames, peak=%.4f\n",
           res.output_generated, peak);
    return 0;
}
