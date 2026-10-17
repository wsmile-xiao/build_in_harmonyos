/* test_ohos.c — HarmonyOS 专项测试 for audio-resampler 0.7.
 *
 * OHOS 适配要点验证：通过公开 API 以多线程模式（RESAMPLE_MULTITHREADED，
 * workers.c pthread 路径）运行 44.1k->48k 固定比率重采样，断言输出帧数与
 * 峰值正确。多线程在 OHOS 上依赖 pthread 正常可执行，这是本适配的核心
 * 平台差异点之一（上游 Makefile 仅 Intel gcc 单线程/多线程标志，OHOS
 * clang + pthread 需实证可用）。
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
#define FRAMES 44100   /* 1 s of stereo input */

static float *in[2], *out[2];

int main(void)
{
    Resample *rs = NULL;
    int i, ch;
    double peak = 0.0;
    unsigned int expected;
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
                                BLACKMAN_HARRIS | SUBSAMPLE_INTERPOLATE |
                                RESAMPLE_MULTITHREADED);
    if (!rs) {
        fprintf(stderr, "resampleFixedRatioInit (multithreaded) returned NULL\n");
        free(in[0]); free(in[1]); free(out[0]); free(out[1]);
        return 1;
    }

    expected = resampleGetExpectedOutput(rs, FRAMES, (double) OUT_RATE / (double) IN_RATE);
    res = resampleProcess(rs, (const artsample_t *const *) in, FRAMES,
                          (artsample_t *const *) out, FRAMES * 2,
                          (double) OUT_RATE / (double) IN_RATE);
    if (res.output_generated <= 0) {
        fprintf(stderr, "no output generated (output_generated=%u)\n", res.output_generated);
        resampleFree(rs);
        free(in[0]); free(in[1]); free(out[0]); free(out[1]);
        return 1;
    }
    if (expected > 0 && res.output_generated != expected) {
        fprintf(stderr, "output_generated %u != expected %u\n",
                res.output_generated, expected);
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

    printf("OHOS PASS: multithreaded 44.1k->48k resampler generated %u/%u frames, peak=%.4f\n",
           res.output_generated, expected, peak);
    return 0;
}
