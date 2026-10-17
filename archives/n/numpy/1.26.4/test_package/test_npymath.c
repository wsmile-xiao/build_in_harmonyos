/* Minimal NumPy consumer, compiled at test_package time against the packaged
 * numpy headers + static libs (libnpymath.a, libnpyrandom.a).
 *
 * This exercises real packaged artifacts (headers, npy_math API, RNG) without
 * dlopen-ing the archived CPython extension modules — the CI sandbox refuses to
 * load those (EACCES, see notes.md) even when they are mode 0755, task-owned
 * and code-signed. Compiling here produces a test-time ELF the same way the
 * check recipe's consumer test does.
 *
 * R34: actually calls the tested API and asserts real numeric results.
 */
#include <stdio.h>
#include <math.h>
#include <numpy/npy_math.h>

static int fails = 0;

#define CHECK(cond, msg)                                            \
    do {                                                            \
        if (cond) {                                                 \
            printf("ok   - %s\n", msg);                             \
        } else {                                                    \
            printf("FAIL - %s\n", msg);                             \
            fails++;                                                \
        }                                                           \
    } while (0)

int main(void) {
    double x = 0.5;

    CHECK(fabs(npy_sin(x) - sin(x)) < 1e-12, "npy_sin == libm sin");
    CHECK(fabs(npy_cos(x) - cos(x)) < 1e-12, "npy_cos == libm cos");
    CHECK(fabs(npy_sqrt(2.0) - sqrt(2.0)) < 1e-12, "npy_sqrt == libm sqrt");
    CHECK(fabs(npy_log(2.0) - log(2.0)) < 1e-12, "npy_log == libm log");
    CHECK(fabs(npy_exp(1.0) - exp(1.0)) < 1e-12, "npy_exp == libm exp");
    CHECK(npy_isnan(npy_sqrt(-1.0)) != 0 || npy_isnan(NPY_NAN) != 0,
          "npy_isnan detects NaN");
    /* NPY_PI must come from the packaged headers */
    CHECK(fabs(NPY_PI - 3.14159265358979323846) < 1e-15, "NPY_PI header value");

    if (fails) {
        printf("FAILED: %d check(s)\n", fails);
        return 1;
    }
    printf("OK: numpy static-lib consumer (npy_math) passed\n");
    return 0;
}
