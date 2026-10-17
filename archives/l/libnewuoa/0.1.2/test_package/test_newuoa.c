/* Consumer test for libnewuoa: minimize a strictly convex quadratic and
 * assert both the objective value and the minimizer converge. */
#include <math.h>
#include <stdio.h>

#include "newuoa.h"

static double quad(long n, const double *x) {
    (void)n;
    double dx0 = x[0] - 3.0;
    double dx1 = x[1] + 1.0;
    return dx0 * dx0 + dx1 * dx1 + 7.0;
}

int main(void) {
    double x[2] = {0.0, 0.0};
    double w[256];
    long n = 2;
    long npt = 5; /* in [N+2, (N+1)(N+2)/2] = [4, 6] */
    long maxfun = 5000;

    double f = newuoa(quad, n, npt, x, 1.0, 1e-6, maxfun, w);
    printf("newuoa: f=%g x=(%.6f,%.6f)\n", f, x[0], x[1]);

    if (fabs(f - 7.0) > 1e-3) {
        fprintf(stderr, "FAIL: objective %.6f did not converge to 7\n", f);
        return 1;
    }
    if (fabs(x[0] - 3.0) > 1e-2 || fabs(x[1] + 1.0) > 1e-2) {
        fprintf(stderr, "FAIL: minimizer (%.6f,%.6f) != (3,-1)\n", x[0], x[1]);
        return 1;
    }
    printf("PASS\n");
    return 0;
}
