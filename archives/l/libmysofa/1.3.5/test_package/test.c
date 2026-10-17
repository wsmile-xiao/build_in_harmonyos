/*
 * test_package consumer test for libmysofa 1.3.5 on HarmonyOS PC
 * (aarch64-linux-ohos).
 *
 * Actually exercises the packaged libmysofa public API (R34): open a real
 * SOFA file via mysofa_open(), fetch a filter with mysofa_getfilter_float(),
 * and verify the produced filter values are finite and the delay sane.
 *
 * NOTE: uses CHECK() instead of assert() so the validation still runs under
 * Release (-DNDEBUG) builds.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include "mysofa.h"

#define CHECK(expr)                                                     \
    do {                                                                \
        if (!(expr)) {                                                  \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__,     \
                    #expr);                                             \
            return 1;                                                   \
        }                                                               \
    } while (0)

int main(void) {
    struct MYSOFA_EASY *easy;
    int err = 0;
    int filterlength = 0;
    int i;

    easy = mysofa_open("data/testfile.sofa", 48000, &filterlength, &err);
    CHECK(easy != NULL);
    CHECK(err == 0);
    CHECK(filterlength > 0);
    CHECK(easy->hrtf != NULL);
    CHECK(easy->hrtf->M > 0);
    CHECK(easy->hrtf->N > 0);
    CHECK(easy->hrtf->R >= 2);

    {
        float *ir_l = (float *)malloc(easy->hrtf->N * sizeof(float));
        float *ir_r = (float *)malloc(easy->hrtf->N * sizeof(float));
        float delay_l = 0.0f, delay_r = 0.0f;
        float coord[3] = {0.0f, 0.0f, 1.0f};
        CHECK(ir_l != NULL && ir_r != NULL);

        mysofa_s2c(coord);
        mysofa_getfilter_float(easy, coord[0], coord[1], coord[2], ir_l,
                               ir_r, &delay_l, &delay_r);
        for (i = 0; i < easy->hrtf->N; i++) {
            CHECK(isfinite(ir_l[i]));
            CHECK(isfinite(ir_r[i]));
        }
        CHECK(isfinite(delay_l));
        CHECK(delay_l >= 0.0f);

        free(ir_l);
        free(ir_r);
    }

    printf("libmysofa consumer test: PASSED (M=%d N=%d R=%d)\n",
           easy->hrtf->M, easy->hrtf->N, easy->hrtf->R);
    mysofa_close(easy);
    return 0;
}
