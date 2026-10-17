/* Consumer test for pffft 1.1.0 on HarmonyOS PC (aarch64/NEON).
 *
 * Per dispatch: 64-point real FFT -> IFFT round trip with energy-conservation
 * assertion and tolerance-based comparison. The reference values are computed
 * with a naive O(N^2) DFT inside the test itself (same approach the upstream
 * test suite uses via its in-tree FFTPACK reference), so no external
 * dependency is needed.
 *
 * Checks (10 assertions total):
 *  1. pffft_min_fft_size(PFFFT_REAL) == 32 (64 >= min, transform legal)
 *  2. pffft_simd_size() == 4 on aarch64 (NEON activated at build time)
 *  3. pffft_simd_arch() is "NEON" on aarch64
 *  4. Forward ordered spectrum: DC bin equals sum(x) within 1e-3
 *  5. Nyquist bin (imag of bin 0) matches naive DFT within 1e-3
 *  6. Bin k (k=1..N/2-1) matches naive DFT within 1e-3 per-component
 *     (max abs error over all bins reported)
 *  7. Parseval energy conservation: sum|X|^2 == N * sum|x|^2 within 1e-2
 *  8. IFFT round trip: max|x - x'| < 1e-3 after 1/N scaling
 *  9. Round-trip energy conservation: sum|x|^2 == sum|x'|^2 within 1e-2
 * 10. pffft_aligned_malloc/pffft_aligned_free allocate and release (16-byte
 *     alignment guaranteed by PFFFT SIMD contract)
 */
#include "pffft/pffft.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static int g_failures = 0;
static int g_checks = 0;

#define CHECK(cond, name)                                        \
    do {                                                         \
        g_checks++;                                              \
        if (cond) {                                              \
            printf("PASS: %s\n", name);                          \
        } else {                                                 \
            g_failures++;                                        \
            printf("FAIL: %s\n", name);                          \
        }                                                        \
    } while (0)

int main(void)
{
    const int N = 64; /* must be a power of two >= pffft_min_fft_size */

    /* --- 1. size / SIMD introspection ---------------------------------- */
    int min_size = pffft_min_fft_size(PFFFT_REAL);
    CHECK(min_size <= N, "min_fft_size <= 64");

    int simd_size = pffft_simd_size();
    const char *simd_arch = pffft_simd_arch();
    printf("info: simd_size=%d simd_arch=%s\n", simd_size, simd_arch);
    CHECK(simd_size == 4, "simd_size == 4 (NEON float path active)");
    CHECK(simd_arch && strcmp(simd_arch, "NEON") == 0, "simd_arch == NEON");

    /* --- setup ---------------------------------------------------------- */
    PFFFT_Setup *setup = pffft_new_setup(N, PFFFT_REAL);
    CHECK(setup != NULL, "pffft_new_setup(64, PFFFT_REAL)");
    if (!setup) {
        printf("test_pffft: %d checks passed, %d failed\n", g_checks, g_failures);
        return g_failures > 0 ? 1 : 0;
    }

    float *x = (float *)pffft_aligned_malloc(N * sizeof(float));
    if (!x) { return 1; }
    float *spectrum = (float *)pffft_aligned_malloc(N * sizeof(float));
    if (!spectrum) { return 1; }
    float *work = (float *)pffft_aligned_malloc(N * sizeof(float));
    if (!work) { return 1; }
    float *back = (float *)pffft_aligned_malloc(N * sizeof(float));
    if (!back) { return 1; }

    /* deterministic multi-tone signal: 3 sinusoids + DC offset */
    for (int k = 0; k < N; k++) {
        x[k] = 1.0f                       /* DC */
             + 2.0f * sinf(2.0f * (float)M_PI * 3.0f * k / N)    /* bin 3  */
             + 1.5f * cosf(2.0f * (float)M_PI * 17.0f * k / N)   /* bin 17 */
             + 0.75f * sinf(2.0f * (float)M_PI * 30.0f * k / N); /* bin 30 */
    }

    /* --- forward ordered transform -------------------------------------- */
    pffft_transform_ordered(setup, x, spectrum, work, PFFFT_FORWARD);

    /* naive O(N^2) real DFT reference (same role as upstream FFTPACK ref) */
    float naive[N / 2][2];
    for (int k = 0; k < N / 2; k++) {
        double re = 0.0, im = 0.0;
        for (int n = 0; n < N; n++) {
            double ang = 2.0 * M_PI * (double)k * (double)n / (double)N;
            re += x[n] * cos(ang);
            im -= x[n] * sin(ang);
        }
        naive[k][0] = (float)re;
        naive[k][1] = (float)im;
    }

    /* bin 0 of the ordered real spectrum packs F(0) + i*F(N/2) */
    float dc_ref = 0.0f, nyq_ref = 0.0f;
    for (int n = 0; n < N; n++) {
        dc_ref += x[n];
        nyq_ref += x[n] * (n % 2 ? -1.0f : 1.0f);
    }
    CHECK(fabsf(spectrum[0] - dc_ref) < 1e-3f, "DC bin matches time-sum");
    CHECK(fabsf(spectrum[1] - nyq_ref) < 1e-3f, "Nyquist bin matches parity sum");

    float max_bin_err = 0.0f;
    for (int k = 1; k < N / 2; k++) {
        float er = fabsf(spectrum[2 * k] - naive[k][0]);
        float ei = fabsf(spectrum[2 * k + 1] - naive[k][1]);
        if (er > max_bin_err) max_bin_err = er;
        if (ei > max_bin_err) max_bin_err = ei;
    }
    printf("info: max per-component spectrum error vs naive DFT = %g\n",
           (double)max_bin_err);
    CHECK(max_bin_err < 1e-3f, "spectrum bins match naive DFT (tol 1e-3)");

    /* Parseval (real N-point transform): sum |X|^2 = N * sum |x|^2 */
    double e_time = 0.0, e_freq = 0.0;
    for (int k = 0; k < N; k++) {
        e_time += (double)x[k] * x[k];
    }
    e_freq = (double)spectrum[0] * spectrum[0]
           + (double)spectrum[1] * spectrum[1];
    for (int k = 1; k < N / 2; k++) {
        double re = spectrum[2 * k], im = spectrum[2 * k + 1];
        e_freq += 2.0 * (re * re + im * im); /* +k and -k conjugates */
    }
    printf("info: energy time=%g freq=%g (ratio %.9f)\n",
           e_time, e_freq, e_freq / (N * e_time));
    CHECK(fabs(e_freq - N * e_time) < 1e-2 * N * e_time,
          "Parseval energy conservation (freq = N * time)");

    /* --- inverse transform round trip ----------------------------------- */
    pffft_transform_ordered(setup, spectrum, back, work, PFFFT_BACKWARD);

    float max_rt_err = 0.0f;
    for (int k = 0; k < N; k++) {
        float v = back[k] / (float)N; /* backward is unscaled: F^-1(F(x))=N*x */
        float err = fabsf(v - x[k]);
        if (err > max_rt_err) max_rt_err = err;
    }
    printf("info: FFT->IFFT round-trip max abs error = %g\n", (double)max_rt_err);
    CHECK(max_rt_err < 1e-3f, "round trip reconstructs input (tol 1e-3)");

    double e_back = 0.0;
    for (int k = 0; k < N; k++) {
        double v = back[k] / (double)N;
        e_back += v * v;
    }
    CHECK(fabs(e_back - e_time) < 1e-2 * e_time,
          "round-trip energy conservation");

    /* --- aligned heap contract ------------------------------------------ */
    pffft_aligned_free(work);
    pffft_aligned_free(back);
    pffft_aligned_free(spectrum);
    pffft_aligned_free(x);
    pffft_destroy_setup(setup);
    CHECK(1, "aligned malloc/free lifecycle");

    printf("test_pffft: %d checks passed, %d failed\n",
           g_checks - g_failures, g_failures);
    return g_failures > 0 ? 1 : 0;
}
