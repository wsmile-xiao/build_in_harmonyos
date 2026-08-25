#include <stdio.h>
#include <stdlib.h>
#include <z3.h>

int main(void) {
    Z3_config cfg = Z3_mk_config();
    Z3_context ctx = Z3_mk_context(cfg);
    Z3_solver solver = Z3_mk_solver(ctx);

    /* Declare a constant x of type Int */
    Z3_sort int_sort = Z3_mk_int_sort(ctx);
    Z3_symbol x_sym = Z3_mk_int_symbol(ctx, 0);
    Z3_ast x = Z3_mk_const(ctx, x_sym, int_sort);

    /* Assert x > 100 */
    Z3_ast hundred = Z3_mk_int(ctx, 100, int_sort);
    Z3_ast x_gt_100 = Z3_mk_gt(ctx, x, hundred);
    Z3_solver_assert(ctx, solver, x_gt_100);

    /* Check satisfiability */
    Z3_lbool result = Z3_solver_check(ctx, solver);

    int ret;
    if (result == Z3_L_TRUE) {
        printf("z3 test: sat (correct)\n");
        ret = 0;
    } else {
        printf("z3 test: unexpected result (expected sat)\n");
        ret = 1;
    }

    Z3_solver_dec_ref(ctx, solver);
    Z3_del_context(ctx);
    Z3_del_config(cfg);
    return ret;
}
