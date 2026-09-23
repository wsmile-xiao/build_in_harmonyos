/*
 * test_package consumer test for cmsis-dsp 1.18.0 (OHOS aarch64).
 * R34: actually calls the packaged public API and verifies observable results.
 * Uses only public headers installed via <CMSIS-DSP/arm_math.h>.
 */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "arm_math.h"

int main(void)
{
    /* Public API: arm_dot_prod_f32 (Statistics/Functional group, installed header) */
    const float32_t a[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    const float32_t b[4] = {4.0f, 3.0f, 2.0f, 1.0f};
    float32_t dot = 0.0f;
    arm_dot_prod_f32(a, b, 4, &dot);
    /* 1*4 + 2*3 + 3*2 + 4*1 = 20 */

    /* Public API: arm_sqrt_f32 (FastMath group) */
    float32_t sq = 0.0f;
    arm_status st = arm_sqrt_f32(16.0f, &sq);

    /* Public API: arm_mean_f32 (Statistics group) */
    float32_t mean = 0.0f;
    arm_mean_f32(a, 4, &mean);

    printf("dot=%.1f sqrt=%.1f mean=%.2f arm_status=%d\n", dot, sq, mean, (int)st);
    if (fabsf(dot - 20.0f) > 1e-4f) { printf("FAIL dot\n"); return 1; }
    if (fabsf(sq - 4.0f) > 1e-4f)  { printf("FAIL sqrt\n"); return 2; }
    if (fabsf(mean - 2.5f) > 1e-4f){ printf("FAIL mean\n"); return 3; }
    if (st != ARM_MATH_SUCCESS)    { printf("FAIL status\n"); return 4; }
    printf("test_package cmsis-dsp 1.18.0: OK\n");
    return 0;
}