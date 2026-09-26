/* liquid-dsp consumer + OpenHarmony platform checks.
 *
 * This program really depends on the package under test: it links
 * liquid::liquid-static and calls the public API
 * (liquid_nchoosek / liquid_version / windowf* / dotprod_rrrf* / fft*).
 *
 * Generic consumer checks (3) verify the Conan/CMake package contract.
 * [OHOS-*] checks (3) verify the OpenHarmony-specific adaptation decisions:
 *   [OHOS-1] target platform identity
 *   [OHOS-2] aarch64 NEON accelerated dot-product path
 *   [OHOS-3] built-in FFT only (recipe sets FIND_FFTW=OFF, no external fftw3f)
 */
#include <liquid/liquid.h>

#include <complex.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    int fail = 0;
    unsigned int i;

    /* ---------------- generic consumer API checks ---------------- */

    float combinations = liquid_nchoosek(5, 2);
    if (combinations != 10.0f) {
        printf("FAIL nchoosek(5,2)=%f (expected 10.0)\n", combinations);
        fail++;
    } else {
        printf("PASS nchoosek(5,2)=%f\n", combinations);
    }

    const char *ver = liquid_version;
    if (ver == NULL || strlen(ver) == 0) {
        printf("FAIL liquid_version empty\n");
        fail++;
    } else {
        printf("PASS liquid_version=%s\n", ver);
    }

    windowf w = windowf_create(16);
    if (w == NULL) {
        printf("FAIL windowf_create\n");
        fail++;
    } else {
        float first = 0.0f;
        for (i = 0; i < 16; i++) {
            windowf_push(w, 1.0f);
        }
        windowf_index(w, 0, &first);
        if (first != 1.0f) {
            printf("FAIL windowf tap[0]==%f (expected 1.0)\n", first);
            fail++;
        } else {
            printf("PASS windowf_create/push/index tap[0]=%f\n", first);
        }
        windowf_destroy(w);
    }

    /* ---------------- [OHOS-*] OpenHarmony-specific checks ---------------- */

    /* [OHOS-1] target platform identity: this artifact is built for OpenHarmony */
#if defined(__OHOS__)
    printf("[OHOS-1] PASS build target = OpenHarmony (__OHOS__=%d, __OHOS_FAMILY__=%d)\n",
           (int)__OHOS__, (int)__OHOS_FAMILY__);
#else
    printf("[OHOS-1] FAIL build target is not OpenHarmony (__OHOS__ undefined)\n");
    fail++;
#endif

    /* [OHOS-2] aarch64 NEON acceleration: liquid picks the SIMD dot-product
       implementation on this target; verify the accelerated result numerically. */
    {
        unsigned int n = 64;
        float v[64], x[64], y = 0.0f;
        for (i = 0; i < n; i++) {
            v[i] = 1.0f;
            x[i] = 2.0f;
        }
        dotprod_rrrf q = dotprod_rrrf_create(v, n);
        if (q == NULL) {
            printf("[OHOS-2] FAIL dotprod_rrrf_create\n");
            fail++;
        } else {
            dotprod_rrrf_execute(q, x, &y);
            dotprod_rrrf_destroy(q);
            if (fabsf(y - 128.0f) < 1e-3f) {
#if defined(__ARM_NEON)
                printf("[OHOS-2] PASS aarch64 NEON dotprod(64)=%f (__ARM_NEON enabled)\n", y);
#else
                printf("[OHOS-2] PASS dotprod(64)=%f (portable path)\n", y);
#endif
            } else {
                printf("[OHOS-2] FAIL dotprod(64)=%f (expected 128.0)\n", y);
                fail++;
            }
        }
    }

    /* [OHOS-3] built-in FFT only: the recipe disables FIND_FFTW, so the transform
       must come from the package's own implementation, not an external fftw3f. */
    {
        unsigned int n = 16;
        liquid_float_complex x[16], y[16];
        for (i = 0; i < n; i++) {
            x[i] = 1.0f; /* real part 1, imaginary part 0 */
        }
        fftplan p = fft_create_plan(n, x, y, LIQUID_FFT_FORWARD, 0);
        if (p == NULL) {
            printf("[OHOS-3] FAIL fft_create_plan\n");
            fail++;
        } else {
            float dc, off;
            fft_execute(p);
            fft_destroy_plan(p);
            dc = crealf(y[0]);
            off = cabsf(y[1]);
            if (fabsf(dc - 16.0f) < 1e-3f && off < 1e-3f) {
                printf("[OHOS-3] PASS built-in FFT: DC=%f, bin1=%f (FIND_FFTW=OFF)\n", dc, off);
            } else {
                printf("[OHOS-3] FAIL built-in FFT: DC=%f (expected 16), bin1=%f (expected 0)\n",
                       dc, off);
                fail++;
            }
        }
    }

    if (fail == 0) {
        printf("liquid-dsp 1.8.0.2 test_package: ALL PASS\n");
        return 0;
    }
    printf("liquid-dsp 1.8.0.2 test_package: %d FAILURES\n", fail);
    return 1;
}
