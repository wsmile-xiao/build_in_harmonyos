/* Consumer test for yices/2.7.0: drives the yices C API to solve a
 * trivial UNSAT instance and a SAT instance, asserting exact results.
 */
#include <stdio.h>
#include <stdlib.h>

#include "yices.h"

int main(void) {
    int failures = 0;

    /* version string present */
    const char *v = yices_version;
    printf("yices version: %s\n", v);
    if (!v || v[0] != '2') {
        printf("FAIL: version\n");
        failures++;
    } else {
        printf("ok: version\n");
    }

    yices_init();

    /* UNSAT: x > 0 && x < 0 over integers */
    type_t int_t = yices_int_type();
    term_t x = yices_new_uninterpreted_term(int_t);
    term_t zero = yices_zero();
    term_t gt = yices_arith_gt_atom(x, zero);
    term_t lt = yices_arith_lt_atom(x, zero);
    term_t both = yices_and2(gt, lt);

    context_t *ctx = yices_new_context(NULL);
    yices_assert_formula(ctx, both);
    smt_status_t st = yices_check_context(ctx, NULL);
    printf("unsat case: status=%d\n", (int)st);
    if (st != YICES_STATUS_UNSAT) {
        printf("FAIL: expected YICES_STATUS_UNSAT\n");
        failures++;
    } else {
        printf("ok: unsat case\n");
    }
    yices_free_context(ctx);

    /* SAT: x > 0 over integers */
    ctx = yices_new_context(NULL);
    yices_assert_formula(ctx, gt);
    st = yices_check_context(ctx, NULL);
    printf("sat case: status=%d\n", (int)st);
    if (st != YICES_STATUS_SAT) {
        printf("FAIL: expected YICES_STATUS_SAT\n");
        failures++;
    } else {
        printf("ok: sat case\n");
    }
    yices_free_context(ctx);

    yices_exit();

    printf("failed=%d\n", failures);
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
