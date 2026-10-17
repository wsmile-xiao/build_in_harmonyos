#include <stdio.h>
#include <math.h>

#include <bw_math.h>

int main(void) {
    int failed = 0;

    /* bw_absf: absolute value */
    if (fabsf(bw_absf(-3.5f) - 3.5f) > 1e-6f) {
        printf("FAIL bw_absf(-3.5f)\n");
        failed++;
    }

    /* bw_pow2f: 2^x approximation */
    if (fabsf(bw_pow2f(3.f) - 8.f) > 1e-3f) {
        printf("FAIL bw_pow2f(3.f)\n");
        failed++;
    }

    /* bw_clipf: clipping into [0, 1] */
    if (fabsf(bw_clipf(2.f, 0.f, 1.f) - 1.f) > 1e-6f) {
        printf("FAIL bw_clipf(2.f, 0.f, 1.f)\n");
        failed++;
    }

    if (failed == 0) {
        printf("test brickworks 1.4.3: OK (absf/pow2f/clipf verified)\n");
        return 0;
    }
    printf("test brickworks 1.4.3: %d assertion(s) failed\n", failed);
    return 1;
}
