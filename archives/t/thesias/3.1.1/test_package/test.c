#include <math.h>
#include <stdio.h>
#include <stdlib.h>

/* Consumer test (R34): really calls the public exported C API of
 * libthesiaslib.so shipped by the thesias package and asserts numerical
 * behaviour. THESIAS 3.1.1 exports the bundled Cephes routines with default
 * visibility (verified with nm -D: igam/igamc/igami/chdtr/chdtrc/chdtri/
 * ndtri/lgam are T symbols, as is the JNI entry Java_thesiaslib_thesiasRun),
 * so the library's computational surface is testable without a JVM here.
 * Reference values are fixed double literals independent of libm. */

extern double igam(double a, double x);
extern double igamc(double a, double x);
extern double igami(double a, double y);
extern double chdtr(double df, double x);
extern double chdtri(double df, double y);
extern double ndtri(double y0);
extern double lgam(double x);

static int failures = 0;

static void check(const char *name, double got, double want, double tol) {
    if (fabs(got - want) > tol) {
        fprintf(stderr, "FAIL %s: got %.17g want %.17g\n", name, got, want);
        failures++;
    } else {
        printf("ok   %s = %.17g\n", name, got);
    }
}

int main(void) {
    /* ndtri(0.975) = standard normal 97.5% quantile z_0.975 */
    check("ndtri(0.975)", ndtri(0.975), 1.959963984540054, 1e-9);
    /* lgam(5.0) = ln(5!) = ln(24) */
    check("lgam(5.0)", lgam(5.0), 3.1780538303479458, 1e-9);
    /* igam(0.5, 1.0) = P(1/2, 1) = erf(sqrt(1)) */
    check("igam(0.5, 1.0)", igam(0.5, 1.0), 0.8427007929497149, 1e-9);
    /* igamc(0.5, 1.0) = Q(1/2, 1) = erfc(1) */
    check("igamc(0.5, 1.0)", igamc(0.5, 1.0), 0.15729920705028513, 1e-9);
    /* chdtr(1, 3.841458820694124) = chi^2_1 CDF at its 95% quantile */
    check("chdtr(1, 3.841458820694124)", chdtr(1.0, 3.841458820694124), 0.95, 1e-6);
    /* chdtri(3, 0.05) = chi^2_3 95% quantile */
    check("chdtri(3, 0.05)", chdtri(3.0, 0.05), 7.81472790325118, 1e-6);
    /* igami is the inverse of igamc: igami(0.5, erfc(1)) = 1.0 */
    check("igami(0.5, erfc(1))", igami(0.5, 0.15729920705028513), 1.0, 1e-6);

    if (failures != 0) {
        fprintf(stderr, "test_thesias: %d assertion(s) FAILED\n", failures);
        return 1;
    }
    printf("test_thesias: 7/7 Cephes assertions passed\n");
    return 0;
}
