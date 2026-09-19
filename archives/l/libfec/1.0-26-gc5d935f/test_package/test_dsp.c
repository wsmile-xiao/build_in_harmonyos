/* test_dsp.c — DSP primitive consumer test for the packaged libfec.
 *
 * Cross-checks the dot product, sum-of-squares and peak-value primitives
 * against plain scalar reference loops over deterministic data, including
 * a non-zero-offset window (the documented usage in upstream peaktest.c).
 * peakval() is a public library symbol although upstream declares it only
 * inside peaktest.c, so it is declared here the same way.
 */
#include <stdio.h>

#include "fec.h"

#define LEN 61
#define OFFSET 7

int peakval(signed short *, int); /* public symbol, not in fec.h upstream */

static signed short coeffs[LEN];
static signed short input[LEN];

static unsigned long lcg_state = 0x0badf00dUL;
static unsigned int lcg(void)
{
    lcg_state = lcg_state * 1103515245UL + 12345UL;
    return (unsigned int)((lcg_state >> 16) & 0xffff);
}

int main(void)
{
    int i;
    int failures = 0;
    int checks = 0;
    long expect_dot = 0;
    unsigned long long expect_sumsq = 0;
    int expect_peak = 0;
    long got_dot;
    unsigned long long got_sumsq;
    int got_peak;
    void *dp;

    for (i = 0; i < LEN; i++) {
        coeffs[i] = (signed short)(lcg() & 0xffff); /* full signed range */
        input[i] = (signed short)(lcg() % 600u - 300u);
        expect_dot += (long)coeffs[i] * (long)input[i];
        expect_sumsq += (long long)input[i] * (long long)input[i];
        {
            int a = input[i] < 0 ? -input[i] : input[i];
            if (a > expect_peak) {
                expect_peak = a;
            }
        }
    }

    /* dotprod over the whole buffer */
    dp = initdp(coeffs, LEN);
    checks++;
    if (dp == NULL) {
        printf("FAIL initdp returned NULL\n");
        return 1;
    }
    got_dot = dotprod(dp, input);
    checks++;
    if (got_dot != expect_dot) {
        failures++;
        printf("FAIL dotprod: got %ld expected %ld\n", got_dot, expect_dot);
    }
    freedp(dp);

    /* sumsq over the whole buffer */
    got_sumsq = sumsq(input, LEN);
    checks++;
    if (got_sumsq != expect_sumsq) {
        failures++;
        printf("FAIL sumsq: got %llu expected %llu\n", got_sumsq, expect_sumsq);
    }

    /* peakval over a non-zero-offset window */
    expect_peak = 0;
    for (i = OFFSET; i < LEN; i++) {
        int a = input[i] < 0 ? -input[i] : input[i];
        if (a > expect_peak) {
            expect_peak = a;
        }
    }
    got_peak = peakval(&input[OFFSET], LEN - OFFSET);
    checks++;
    if (got_peak != expect_peak) {
        failures++;
        printf("FAIL peakval: got %d expected %d\n", got_peak, expect_peak);
    }

    printf("test_dsp: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
