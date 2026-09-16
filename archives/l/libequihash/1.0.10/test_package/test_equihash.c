/* Consumer test for libequihash — exercises the real public C API.
 *
 * Four checks (tiny N=24/K=3 parameters keep solve() instant):
 *   1. solsize() matches the documented size formula.
 *   2. solve() finds a solution for a fixed seed.
 *   3. verify() accepts the genuine solution.
 *   4. verify() rejects a tampered solution.
 *
 * Prints one CASE line per check plus a "RESULT: N passed, M failed"
 * trailer parsed by test_package/conanfile.py for evidence.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif
#include "equihash.h"
#ifdef __cplusplus
}
#endif

static int g_passed = 0;
static int g_failed = 0;

static void check(int cond, const char *name, const char *detail)
{
    int idx = g_passed + g_failed + 1;
    if (cond) {
        g_passed++;
        printf("CASE %d: PASS (%s %s)\n", idx, name, detail);
    } else {
        g_failed++;
        printf("CASE %d: FAIL (%s %s)\n", idx, name, detail);
    }
}

int main(void)
{
    /* Tiny parameters: real PoW work, millisecond runtime. */
    const unsigned n = 24;
    const unsigned k = 3;
    static const uint8_t seed[] = "libequihash-test-seed-01";
    const size_t seed_len = sizeof(seed) - 1;

    /* Case 1: solsize() matches (1<<k) * ((n/(k+1)) + 1) / 8 + 4. */
    {
        size_t expect = ((size_t)(1u << k)) * ((n / (k + 1)) + 1) / 8 + 4;
        check(solsize(n, k) == expect, "solsize", "formula-value-11");
    }

    /* Case 2: solve() finds a solution for the fixed seed. */
    size_t sol_len = solsize(n, k);
    uint8_t sol[64];
    int solved = 0;
    if (sol_len <= sizeof(sol)) {
        solved = solve(n, k, seed, seed_len, sol, sol_len);
    }
    check(solved == 1, "solve", "fixed-seed");

    /* Case 3: verify() accepts the genuine solution. */
    check(solved == 1 && verify(n, k, seed, seed_len, sol, sol_len) == 1,
          "verify-accept", "genuine-solution");

    /* Case 4: verify() rejects a tampered solution (negative control). */
    {
        int rejected = 0;
        if (solved == 1) {
            uint8_t bad[64];
            memcpy(bad, sol, sol_len);
            bad[sol_len - 1] ^= 0xFF;
            rejected = (verify(n, k, seed, seed_len, bad, sol_len) == 0);
        }
        check(rejected == 1, "verify-reject", "tampered-solution");
    }

    printf("RESULT: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
