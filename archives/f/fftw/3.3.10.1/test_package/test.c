#include <math.h>
#include <stdio.h>

#include <fftw3.h>

int main(void) {
    fftw_complex in[4];
    fftw_complex out[4];

    for (int i = 0; i < 4; ++i) {
        in[i][0] = (double)i;
        in[i][1] = 0.0;
    }

    fftw_plan plan = fftw_plan_dft_1d(4, in, out, FFTW_FORWARD, FFTW_ESTIMATE);
    if (!plan) {
        if (fprintf(stderr, "fftw_plan_dft_1d failed\n") < 0) {
            return 2;
        }
        return 1;
    }

    fftw_execute(plan);
    fftw_destroy_plan(plan);
    fftw_cleanup();

    if (fabs(out[0][0] - 6.0) > 1e-9 || fabs(out[0][1]) > 1e-9) {
        if (fprintf(stderr, "unexpected fft result: %f + %fi\n",
                    out[0][0], out[0][1]) < 0) {
            return 2;
        }
        return 1;
    }

    if (printf("test fftw 3.3.10.1: DFT smoke test OK\n") < 0) {
        return 2;
    }
    return 0;
}
