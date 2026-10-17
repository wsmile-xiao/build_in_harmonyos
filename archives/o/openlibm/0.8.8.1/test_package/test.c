/*
 * HarmonyOS (aarch64) specific test for openlibm 0.8.8.1.
 *
 * This is a REAL executable test (R34): it links against libopenlibm and
 * asserts numerical results of the library on the OHOS aarch64 target,
 * covering:
 *   1. core double functions (sin/cos/exp/pow/tgamma) vs known constants
 *   2. aarch64 ld128 long-double path (e_sqrtl/e_powl/e_expl/... are only
 *      compiled for aarch64/riscv64 via the ld128/ tree)
 *   3. openlibm fenv (feclearexcept/feraiseexcept/fetestexcept) round-trip
 *      using openlibm_fenv.h (aarch64 fenv.c is OHOS-specific glue)
 * Any failed assertion exits non-zero so CI/conan create catches it.
 */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "openlibm.h"
#include "openlibm_fenv.h"

#define CHECK(cond, msg) do { \
        if (!(cond)) { \
            printf("FAIL: %s\n", msg); \
            exit(1); \
        } \
        printf("PASS: %s\n", msg); \
    } while (0)

static int near(double a, double b, double eps)
{
    double d = a - b;
    if (d < 0) d = -d;
    return d <= eps;
}

int main(void)
{
    printf("openlibm %s HarmonyOS aarch64 specific test\n", "0.8.8.1");

    /* 1. core double functions vs known constants */
    CHECK(near(sin(0.0), 0.0, 1e-15), "sin(0)==0");
    CHECK(near(cos(0.0), 1.0, 1e-15), "cos(0)==1");
    CHECK(near(exp(1.0), 2.718281828459045, 1e-14), "exp(1)==e");
    CHECK(near(pow(2.0, 10.0), 1024.0, 1e-12), "pow(2,10)==1024");
    CHECK(near(tgamma(0.5), 1.772453850905516, 1e-14), "tgamma(0.5)==sqrt(pi)");
    CHECK(near(sqrt(2.0), 1.4142135623730951, 1e-14), "sqrt(2)");
    CHECK(near(log(2.0), 0.6931471805599453, 1e-14), "log(2)");

    /* 2. aarch64 ld128 long-double path (ld128/ tree is aarch64-specific) */
    CHECK(near((double)sqrtl((long double)2.0), 1.4142135623730951, 1e-14), "sqrtl(2) ld128");
    CHECK(near((double)powl((long double)2.0L, (long double)10.0L), 1024.0, 1e-12), "powl(2,10) ld128");
    CHECK(near((double)expl((long double)1.0L), 2.718281828459045, 1e-13), "expl(1) ld128");
    CHECK(near((double)tanhl((long double)0.5L), 0.46211715726000974, 1e-13), "tanhl(0.5) ld128");

    /* 3. fenv round-trip on OHOS aarch64 (fenv.c in aarch64/) */
    feclearexcept(FE_ALL_EXCEPT);
    feraiseexcept(FE_DIVBYZERO);
    {
        int flags = fetestexcept(FE_DIVBYZERO);
        CHECK((flags & FE_DIVBYZERO) != 0, "fenv FE_DIVBYZERO raised");
    }
    feclearexcept(FE_ALL_EXCEPT);
    CHECK(fetestexcept(FE_ALL_EXCEPT) == 0, "fenv cleared");

    printf("ALL HarmonyOS specific tests passed\n");
    return 0;
}
