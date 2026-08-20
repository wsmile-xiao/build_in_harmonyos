#include <kissat.h>
#include <stdio.h>

int main(void) {
    /* Verify version info */
    const char *version = kissat_version();
    printf("kissat version: %s\n", version);

    /* Test 1: UNSAT problem — (x1) AND (NOT x1) */
    kissat *solver = kissat_init();
    if (!solver) {
        fprintf(stderr, "FAIL: kissat_init() returned NULL\n");
        return 1;
    }

    /* Clause: x1 */
    kissat_add(solver, 1);
    kissat_add(solver, 0);

    /* Clause: NOT x1 */
    kissat_add(solver, -1);
    kissat_add(solver, 0);

    int res = kissat_solve(solver);
    printf("Test 1 (UNSAT): solve result = %d (expected 20)\n", res);
    if (res != 20) {
        fprintf(stderr, "FAIL: expected 20 (UNSAT), got %d\n", res);
        kissat_release(solver);
        return 1;
    }

    kissat_release(solver);

    /* Test 2: SAT problem — (x1 OR x2) */
    solver = kissat_init();
    if (!solver) {
        fprintf(stderr, "FAIL: kissat_init() returned NULL\n");
        return 1;
    }

    /* Clause: x1 OR x2 */
    kissat_add(solver, 1);
    kissat_add(solver, 2);
    kissat_add(solver, 0);

    res = kissat_solve(solver);
    printf("Test 2 (SAT): solve result = %d (expected 10)\n", res);
    if (res != 10) {
        fprintf(stderr, "FAIL: expected 10 (SAT), got %d\n", res);
        kissat_release(solver);
        return 1;
    }

    /* Verify variable assignment */
    int val1 = kissat_value(solver, 1);
    int val2 = kissat_value(solver, 2);
    printf("  x1=%d, x2=%d (at least one should be true)\n", val1, val2);
    if (!(val1 > 0 || val2 > 0)) {
        fprintf(stderr, "FAIL: neither x1 nor x2 is true\n");
        kissat_release(solver);
        return 1;
    }

    kissat_release(solver);

    printf("All kissat tests passed.\n");
    return 0;
}
