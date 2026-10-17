#include <stdio.h>
#include <math.h>
#include <string.h>
#include "kiss_fft.h"

int main(void) {
    int nfft = 8;
    int i;
    kiss_fft_cfg cfg;
    kiss_fft_cpx in_cpx[8];
    kiss_fft_cpx out_cpx[8];
    kiss_fft_cpx inv_out[8];
    double max_err = 0.0;

    /* Create forward FFT configuration */
    cfg = kiss_fft_alloc(nfft, 0, NULL, NULL);
    if (!cfg) {
        fprintf(stderr, "FAIL: kiss_fft_alloc returned NULL\n");
        return 1;
    }

    /* Fill input with a simple sine wave: sin(2*pi*k/N) for k=0..N-1 */
    for (i = 0; i < nfft; i++) {
        in_cpx[i].r = (kiss_fft_scalar)sin(2.0 * 3.14159265358979 * i / nfft);
        in_cpx[i].i = 0;
    }

    /* Forward FFT */
    kiss_fft(cfg, in_cpx, out_cpx);
    kiss_fft_free(cfg);

    /* A sine wave of frequency 1 should have peak energy in bin 1 and bin N-1 */
    /* Verify bin 1 has significant magnitude */
    double mag1 = sqrt((double)out_cpx[1].r * out_cpx[1].r + (double)out_cpx[1].i * out_cpx[1].i);
    double mag0 = sqrt((double)out_cpx[0].r * out_cpx[0].r + (double)out_cpx[0].i * out_cpx[0].i);
    if (mag1 < mag0) {
        fprintf(stderr, "FAIL: expected bin 1 magnitude > bin 0 (got %f vs %f)\n", mag1, mag0);
        return 1;
    }

    /* Inverse FFT to reconstruct original signal */
    cfg = kiss_fft_alloc(nfft, 1, NULL, NULL);
    if (!cfg) {
        fprintf(stderr, "FAIL: inverse kiss_fft_alloc returned NULL\n");
        return 1;
    }
    kiss_fft(cfg, out_cpx, inv_out);
    kiss_fft_free(cfg);

    /* Check reconstruction (kissfft inverse needs scaling by 1/N) */
    for (i = 0; i < nfft; i++) {
        double expected = (double)in_cpx[i].r;
        double actual = (double)inv_out[i].r / nfft;
        double err = fabs(expected - actual);
        if (err > max_err) max_err = err;
    }

    if (max_err > 1e-5) {
        fprintf(stderr, "FAIL: reconstruction error too large (%e)\n", max_err);
        return 1;
    }

    printf("test kissfft 131: OK (FFT forward+inverse, max_err=%e)\n", max_err);
    return 0;
}
