/*
 * Smoke test for liblbfgs: verify library links and a trivial L-BFGS call works.
 */
#include <stdio.h>
#include <stdlib.h>
#include <lbfgs.h>

/* Simple quadratic: f(x) = sum((xi-1)^2), grad = 2*(xi-1) */
static lbfgsfloatval_t evaluate(
    void *instance,
    const lbfgsfloatval_t *x,
    lbfgsfloatval_t *g,
    const int n,
    const lbfgsfloatval_t step)
{
    lbfgsfloatval_t fx = 0.0;
    int i;
    (void)instance;
    (void)step;
    for (i = 0; i < n; i++) {
        lbfgsfloatval_t d = x[i] - 1.0;
        fx += d * d;
        g[i] = 2.0 * d;
    }
    return fx;
}

static int progress(
    void *instance,
    const lbfgsfloatval_t *x,
    const lbfgsfloatval_t *g,
    const lbfgsfloatval_t fx,
    const lbfgsfloatval_t xnorm,
    const lbfgsfloatval_t gnorm,
    const lbfgsfloatval_t step,
    int n,
    int k,
    int ls)
{
    (void)instance; (void)x; (void)g;
    (void)fx; (void)xnorm; (void)gnorm;
    (void)step; (void)n; (void)k; (void)ls;
    return 0;
}

int main(void)
{
    int N = 4;
    lbfgsfloatval_t fx;
    lbfgsfloatval_t *x = lbfgs_malloc(N);
    lbfgs_parameter_t param;
    int ret, i;

    if (x == NULL) {
        fprintf(stderr, "ERROR: Failed to allocate memory.\n");
        return 1;
    }

    for (i = 0; i < N; i++) {
        x[i] = 0.0;
    }

    lbfgs_parameter_init(&param);
    ret = lbfgs(N, x, &fx, evaluate, progress, NULL, &param);

    printf("L-BFGS terminated with code = %d\n", ret);
    printf("  fx = %f", fx);
    for (i = 0; i < N; i++) {
        printf(", x[%d] = %f", i, x[i]);
    }
    printf("\n");

    lbfgs_free(x);

    /* LBFGS_SUCCESS = 0 */
    if (ret == 0) {
        printf("SMOOTH TEST PASSED\n");
        return 0;
    } else {
        fprintf(stderr, "SMOOTH TEST FAILED (code %d)\n", ret);
        return 1;
    }
}
