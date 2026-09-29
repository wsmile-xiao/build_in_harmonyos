/*
 * test_package consumer test for math-sll 1.24
 *
 * Exercises public fixed-point (32.32) math API: dbl2sll / sll2dbl,
 * sllmul, slladd, slldiv, sllsqrt, sllcos — verifying observable results
 * against known values. slldiv is implemented as x * sllinv(y) (iterative
 * reciprocal), so its result carries a small rounding error: those checks
 * use a tolerance. This is NOT an empty shell: each call asserts a numeric
 * outcome and exits non-zero on first failure.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "math-sll.h"

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s (%s:%d)\n", msg, __FILE__, __LINE__);   \
            return 1;                                                        \
        }                                                                    \
    } while (0)

#define CHECK_NEAR(got, want, tol, msg)                                      \
    do {                                                                     \
        double _g = (got);                                                   \
        if (fabs(_g - (want)) > (tol)) {                                     \
            fprintf(stderr, "FAIL: %s got=%.10f want=%.10f (%s:%d)\n",       \
                    msg, _g, (double) (want), __FILE__, __LINE__);           \
            return 1;                                                        \
        }                                                                    \
    } while (0)

int main(void)
{
    /* 1.0 in 32.32 fixed point is 2^32 */
    sll one = dbl2sll(1.0);
    CHECK(one == ((sll) 1 << 32), "dbl2sll(1.0) == 1<<32");
    CHECK(sll2dbl(one) == 1.0, "sll2dbl(1<<32) == 1.0");

    /* 0.5 */
    sll half = dbl2sll(0.5);
    CHECK(sll2dbl(half) == 0.5, "sll2dbl(0.5)");

    /* addition: 1.0 + 0.25 = 1.25 */
    sll sum = slladd(one, dbl2sll(0.25));
    CHECK(sll2dbl(sum) == 1.25, "slladd(1.0, 0.25) == 1.25");

    /* multiplication: 1.5 * 2.0 = 3.0 */
    sll prod = sllmul(dbl2sll(1.5), dbl2sll(2.0));
    CHECK(sll2dbl(prod) == 3.0, "sllmul(1.5, 2.0) == 3.0");

    /* division (x * reciprocal(y)): 3.0 / 2.0 ~= 1.5, within tolerance */
    sll quot = slldiv(dbl2sll(3.0), dbl2sll(2.0));
    CHECK_NEAR(sll2dbl(quot), 1.5, 1e-6, "slldiv(3.0, 2.0) ~= 1.5");

    /* sqrt: sqrt(4.0) = 2.0, iterative so tolerance */
    sll root = sllsqrt(dbl2sll(4.0));
    CHECK_NEAR(sll2dbl(root), 2.0, 1e-6, "sllsqrt(4.0) ~= 2.0");

    /* cos(0) = 1.0 */
    sll c = sllcos(dbl2sll(0.0));
    CHECK_NEAR(sll2dbl(c), 1.0, 1e-6, "sllcos(0.0) ~= 1.0");

    /* sin(0) = 0.0 */
    sll s = sllsin(dbl2sll(0.0));
    CHECK_NEAR(sll2dbl(s), 0.0, 1e-6, "sllsin(0.0) ~= 0.0");

    printf("test math-sll 1.24: all %d checks passed\n", 9);
    return 0;
}