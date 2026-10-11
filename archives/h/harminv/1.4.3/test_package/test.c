/* Consumer test for harminv 1.4.3 on HarmonyOS PC
 *
 * Tests the public API by:
 * 1. Creating a signal from known sinusoids
 * 2. Running harmonic inversion
 * 3. Verifying the recovered frequencies match
 *
 * This is a non-trivial consumer test that exercises the library's
 * core algorithm (not just a printf assertion).
 *
 * Upstream reference: sines-test.sh uses:
 *   ./sines 0.1+0.01i 0.08+0.001i | ./harminv 0.05-0.15
 * Expected: frequencies 0.1 and 0.08 with decays 0.01 and 0.001
 */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <complex.h>

#include "harminv.h"

#define PI 3.14159265358979323846
#define TWOPI (2.0 * PI)
#define N 100

/* Generate a complex signal: sum of two damped sinusoids */
static void generate_signal(double complex *signal, int n, double dt,
                            double f1, double decay1,
                            double f2, double decay2)
{
    int i;
    for (i = 0; i < n; i++) {
        double t = i * dt;
        signal[i] = exp(-decay1 * t) * cexp(-I * TWOPI * f1 * t)
                  + exp(-decay2 * t) * cexp(-I * TWOPI * f2 * t);
    }
}

static int double_close(double a, double b, double tol)
{
    return fabs(a - b) < tol;
}

int main(void)
{
    double dt = 1.0;
    double f1 = 0.1;    /* Known frequency 1 */
    double decay1 = 0.01;
    double f2 = 0.08;   /* Known frequency 2 */
    double decay2 = 0.001;

    /* Use a simple real signal (imaginary part = 0) for robustness.
     * harminv works on complex input; a real signal is a special case
     * where all imaginary parts are zero. */
    double complex signal[N];
    harminv_data hd;
    int nf, i;
    int found_f1 = 0, found_f2 = 0;

    printf("=== harminv 1.4.3 consumer test (HarmonyOS) ===\n");

    /* Generate test signal */
    generate_signal(signal, N, dt, f1, decay1, f2, decay2);

    /* Create harminv data structure:
     * fmin=0.05, fmax=0.15, nf=20 (match upstream sines-test.sh range) */
    hd = harminv_data_create(N, signal, 0.05, 0.15, 20);
    if (!hd) {
        fprintf(stderr, "FAIL: harminv_data_create returned NULL\n");
        return 1;
    }

    /* Run harmonic inversion */
    harminv_solve(hd);

    nf = harminv_get_num_freqs(hd);
    printf("Recovered %d frequencies:\n", nf);
    if (nf < 2) {
        fprintf(stderr, "FAIL: expected at least 2 frequencies, got %d\n", nf);
        harminv_data_destroy(hd);
        return 1;
    }

    /* Check recovered frequencies match expected */
    for (i = 0; i < nf; i++) {
        double freq = harminv_get_freq(hd, i);
        double decay = harminv_get_decay(hd, i);
        double err  = harminv_get_freq_error(hd, i);
        printf("  freq[%d] = %.4f, decay = %.6g, error = %.6g\n",
               i, freq, decay, err);

        if (double_close(freq, f1, 0.005)) found_f1 = 1;
        if (double_close(freq, f2, 0.005)) found_f2 = 1;
    }

    harminv_data_destroy(hd);

    if (!found_f1) {
        fprintf(stderr, "FAIL: frequency %.4f not recovered\n", f1);
        return 1;
    }
    if (!found_f2) {
        fprintf(stderr, "FAIL: frequency %.4f not recovered\n", f2);
        return 1;
    }

    printf("PASS: all expected frequencies recovered\n");
    return 0;
}
