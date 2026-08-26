#include <lbfgs.h>
#include <math.h>
#include <stdio.h>

struct solve_state {
    int evaluations;
    int progress_calls;
};

static lbfgsfloatval_t evaluate(void *instance, const lbfgsfloatval_t *x,
                                lbfgsfloatval_t *g, const int n,
                                const lbfgsfloatval_t step)
{
    struct solve_state *state = (struct solve_state *)instance;
    const lbfgsfloatval_t dx = x[0] - 1.0;
    const lbfgsfloatval_t dy = x[1] + 2.0;
    (void)n;
    (void)step;

    state->evaluations++;
    g[0] = 2.0 * dx;
    g[1] = 2.0 * dy;
    return dx * dx + dy * dy;
}

static int progress(void *instance, const lbfgsfloatval_t *x,
                    const lbfgsfloatval_t *g, const lbfgsfloatval_t fx,
                    const lbfgsfloatval_t xnorm, const lbfgsfloatval_t gnorm,
                    const lbfgsfloatval_t step, int n, int k, int ls)
{
    struct solve_state *state = (struct solve_state *)instance;
    (void)x;
    (void)g;
    (void)fx;
    (void)xnorm;
    (void)gnorm;
    (void)step;
    (void)k;
    (void)ls;

    if (n != 2) {
        return 1;
    }
    state->progress_calls++;
    return 0;
}

int main(void)
{
    lbfgsfloatval_t x[2] = {10.0, -7.0};
    lbfgsfloatval_t g[2] = {0.0, 0.0};
    lbfgs_parameter_t param;
    struct solve_state state = {0, 0};
    int ret;
    lbfgsfloatval_t fx;

    lbfgs_parameter_init(&param);
    if (param.m != 6) {
        return 1;
    }
    if (fabs(param.epsilon - 1e-5) > 1e-12) {
        return 2;
    }
    if (param.max_iterations != 0) {
        return 3;
    }
    if (fabs(param.orthantwise_c) > 1e-12) {
        return 4;
    }

    param.max_iterations = 64;
    ret = lbfgs(2, x, evaluate, progress, &state, &param);
    if (ret < 0) {
        return 5;
    }

    fx = evaluate(&state, x, g, 2, 0.0);
    if (fx > 1e-10) {
        return 6;
    }
    if (fabs(x[0] - 1.0) > 1e-5 || fabs(x[1] + 2.0) > 1e-5) {
        return 7;
    }
    if (state.evaluations == 0) {
        return 8;
    }

    printf("liblbfgs/1.1 smoke test passed: ret=%d fx=%g progress=%d\n",
           ret, (double)fx, state.progress_calls);
    return 0;
}
