/*
 * test.c — fftw 2.1.5.1 (single-precision sfftw) functional smoke test.
 *
 * Verifies that the sfftw library really computes a DFT:
 *   in  = [1+0i, 0, 0, 0]  (n=4)
 *   out = [1+0i, 1+0i, 1+0i, 1+0i]  (all ones, since DFT of a delta pulse is constant)
 *
 * API notes: with --enable-type-prefix the installed library is libsfftw.a and
 * the header is sfftw.h, but the public symbols keep the plain `fftw_*` prefix.
 */
#include <sfftw.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

int main(void) {
    const int n = 4;
    fftw_complex in[4], out[4];
    int i, failures = 0;

    /* delta pulse: in[0]=1, rest 0 */
    for (i = 0; i < n; i++) {
        in[i].re = 0.0f;
        in[i].im = 0.0f;
    }
    in[0].re = 1.0f;

    fftw_plan plan = fftw_create_plan(n, FFTW_FORWARD, FFTW_ESTIMATE);
    if (plan == NULL) {
        fprintf(stderr, "FAIL: fftw_create_plan returned NULL\n");
        return 1;
    }

    fftw_one(plan, in, out);
    fftw_destroy_plan(plan);

    /* DFT of delta = all ones */
    for (i = 0; i < n; i++) {
        if (fabsf(out[i].re - 1.0f) > 1e-4f || fabsf(out[i].im) > 1e-4f) {
            fprintf(stderr, "FAIL: out[%d] = (%f, %f), expected (1, 0)\n",
                    i, out[i].re, out[i].im);
            failures++;
        }
    }

    if (failures == 0) {
        printf("sfftw DFT roundtrip OK: out = [1,1,1,1] (all real)\n");
        return 0;
    }
    return 1;
}
