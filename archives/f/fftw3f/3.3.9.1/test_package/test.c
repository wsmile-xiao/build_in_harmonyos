#include <math.h>
#include <stdio.h>
#include <fftw3.h>

static int close_enough(float actual, float expected) {
    return fabsf(actual - expected) < 0.001f;
}

int main(void) {
    fftwf_complex input[4];
    fftwf_complex spectrum[4];
    fftwf_complex output[4];

    input[0][0] = 1.0f; input[0][1] = 0.0f;
    input[1][0] = 2.0f; input[1][1] = 0.0f;
    input[2][0] = 3.0f; input[2][1] = 0.0f;
    input[3][0] = 4.0f; input[3][1] = 0.0f;

    fftwf_plan forward = fftwf_plan_dft_1d(4, input, spectrum, FFTW_FORWARD,
                                           FFTW_ESTIMATE | FFTW_PRESERVE_INPUT);
    fftwf_plan backward = fftwf_plan_dft_1d(4, spectrum, output, FFTW_BACKWARD, FFTW_ESTIMATE);

    if (!forward || !backward) {
        fprintf(stderr, "failed to create fftw3f plans\n");
        if (forward) {
            fftwf_destroy_plan(forward);
        }
        if (backward) {
            fftwf_destroy_plan(backward);
        }
        return 1;
    }

    fftwf_execute(forward);
    fftwf_execute(backward);
    fftwf_destroy_plan(forward);
    fftwf_destroy_plan(backward);

    for (int i = 0; i < 4; ++i) {
        float real = output[i][0] / 4.0f;
        float imag = output[i][1] / 4.0f;
        if (!close_enough(real, input[i][0]) || !close_enough(imag, 0.0f)) {
            fprintf(stderr, "round-trip mismatch at %d: got %f + %fi\n", i, real, imag);
            return 1;
        }
    }

    printf("fftw3f test: OK (single-precision complex FFT round-trip succeeded)\n");
    return 0;
}
