/* Consumer test for rankwidth 0.10 -- drives the real public rw.h API.
 *
 * API source of truth: SageMath rankwidth.pxd
 *   cdef extern from "rw.h":
 *     int init_rw_dec(uint_fast8_t n)
 *     void destroy_rw()
 *     void calculate_level(uint_fast8_t subset_size)
 *     uint_fast8_t get_rw()
 *
 * Four deterministic scenarios on tiny graphs (n <= 4, far below the
 * documented >= 32 vertices limit). Each scenario inits, runs all levels,
 * reads back the rank-width, and destroys. Any failure prints to stderr
 * and returns non-zero; success prints CHECK lines plus a summary.
 */
#include <stdint.h>
#include <stdio.h>

#include "rw.h"

static int check_empty(unsigned n, unsigned max_rw, int idx)
{
    if (init_rw_dec((uint_fast8_t)n) != 0) {
        fprintf(stderr, "CHECK %d: FAIL init_rw_dec(%u) != 0\n", idx, n);
        return 1;
    }
    for (unsigned i = 0; i <= n; ++i) {
        calculate_level((uint_fast8_t)i);
    }
    {
        unsigned rw = (unsigned)get_rw();
        if (rw > max_rw) {
            fprintf(stderr, "CHECK %d: FAIL get_rw()=%u > %u (n=%u)\n",
                    idx, rw, max_rw, n);
            destroy_rw();
            return 1;
        }
        printf("CHECK %d: PASS n=%u rank-width=%u (bound %u)\n",
               idx, n, rw, max_rw);
    }
    destroy_rw();
    return 0;
}

int main(void)
{
    int failures = 0;

    /* Single vertex: no cut exists, rank-width must be 0. */
    failures += check_empty(1, 0, 1);
    /* Two vertices: at most one cut of rank <= 1. */
    failures += check_empty(2, 1, 2);
    /* Three vertices: rank-width bounded by 2. */
    failures += check_empty(3, 2, 3);
    /* Four vertices: still tiny, bounded by 3. Re-init after destroy
       also proves the init/destroy cycle is repeatable (no leaks that
       break a second run). */
    failures += check_empty(4, 3, 4);

    if (failures == 0) {
        printf("ALL CHECKS PASSED (4/4)\n");
        return 0;
    }
    fprintf(stderr, "FAILURES: %d/4\n", failures);
    return 1;
}
