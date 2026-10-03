/*
 * test_package consumer test for nlopt 2.11.0
 * Verifies that the nlopt C API is linked and functional:
 * minimize f(x) = x^2 + 1 over [-10, 10] with COBYLA,
 * expecting optimum near x=0 with minf near 1.
 */
#include <stdio.h>
#include <math.h>
#include <nlopt.h>

static double myfunc(unsigned n, const double *x, double *grad, void *my_func_data)
{
    (void)n; (void)grad; (void)my_func_data;
    return x[0] * x[0] + 1.0;
}

int main(void)
{
    nlopt_opt opt = nlopt_create(NLOPT_LN_COBYLA, 1);
    double lb[1] = {-10.0};
    double ub[1] = {10.0};
    double x[1] = {5.0};
    double minf = 0.0;
    int result;

    if (!opt) {
        printf("nlopt_create failed\n");
        return 1;
    }

    nlopt_set_lower_bounds(opt, lb);
    nlopt_set_upper_bounds(opt, ub);
    nlopt_set_min_objective(opt, myfunc, NULL);
    nlopt_set_xtol_rel(opt, 1e-6);

    result = nlopt_optimize(opt, x, &minf);
    nlopt_destroy(opt);

    if (result < 0) {
        printf("nlopt_optimize failed: %d\n", result);
        return 1;
    }

    printf("nlopt OK: x = %.6f, minf = %.6f\n", x[0], minf);
    if (fabs(x[0]) > 1e-3 || fabs(minf - 1.0) > 1e-3) {
        printf("unexpected optimum\n");
        return 1;
    }
    return 0;
}
