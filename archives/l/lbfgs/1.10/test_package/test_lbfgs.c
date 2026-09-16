/* test_lbfgs.c — lbfgs 1.10 实体消费者测试（带断言）
 *
 * 4 组断言共 12 条：
 *  1) 分配/参数初始化 API（lbfgs_malloc / lbfgs_parameter_init 默认值）
 *  2) 100 维 Rosenbrock 无约束优化收敛（与上游 sample/sample.c 同问题，
 *     上游只打印不断言，此处加 LBFGS_SUCCESS + fx + 解向量断言）
 *  3) OWL-QN L1 正则路径（orthantwise_c=1, BACKTRACKING 线搜索）：
 *     min (x-1)^2+(y-2)^2 + 1*(|x|+|y|) → 软阈值解 (0.5, 1.5)
 *  4) 鸿蒙特有：入参错误路径返回负错误码而非崩溃（上游 sample 与 1~3 组
 *     均不覆盖；OHOS bionic 下非法入参的确定性行为是本适配新增判据）
 */
#include <stdio.h>
#include <math.h>
#include <lbfgs.h>

static int failures = 0;
#define CHECK(cond) do { \
    if (!(cond)) { printf("FAIL: %s\n", #cond); ++failures; } \
} while (0)

static lbfgsfloatval_t rosenbrock(
    void *instance, const lbfgsfloatval_t *x, lbfgsfloatval_t *g,
    const int n, const lbfgsfloatval_t step)
{
    int i;
    lbfgsfloatval_t fx = 0.0;
    for (i = 0; i < n; i += 2) {
        lbfgsfloatval_t t1 = 1.0 - x[i];
        lbfgsfloatval_t t2 = 10.0 * (x[i+1] - x[i] * x[i]);
        g[i+1] = 20.0 * t2;
        g[i] = -2.0 * (x[i] * g[i+1] + t1);
        fx += t1 * t1 + t2 * t2;
    }
    return fx;
}

/* f(x,y) = (x-1)^2 + (y-2)^2（OWL-QN 的 L1 项由库内部处理） */
static lbfgsfloatval_t quadratic(
    void *instance, const lbfgsfloatval_t *x, lbfgsfloatval_t *g,
    const int n, const lbfgsfloatval_t step)
{
    g[0] = 2.0 * (x[0] - 1.0);
    g[1] = 2.0 * (x[1] - 2.0);
    return (x[0] - 1.0) * (x[0] - 1.0) + (x[1] - 2.0) * (x[1] - 2.0);
}

int main(void)
{
    int i, ret;
    lbfgsfloatval_t fx;
    lbfgs_parameter_t param;

    /* 1) 分配/参数初始化 */
    const int N = 100;
    lbfgsfloatval_t *x = lbfgs_malloc(N);
    CHECK(x != NULL);
    lbfgs_parameter_init(&param);
    CHECK(param.m > 0);
    CHECK(param.epsilon > 0);

    /* 2) 100 维 Rosenbrock 收敛到 (1,1,...,1)，fx→0 */
    for (i = 0; i < N; i += 2) { x[i] = -1.2; x[i+1] = 1.0; }
    ret = lbfgs(N, x, &fx, rosenbrock, NULL, NULL, &param);
    CHECK(ret == LBFGS_SUCCESS);
    CHECK(fx < 1e-10);
    CHECK(fabs(x[0] - 1.0) < 1e-5);
    CHECK(fabs(x[1] - 1.0) < 1e-5);
    lbfgs_free(x);

    /* 3) OWL-QN L1 正则：软阈值解 (0.5, 1.5) */
    {
        lbfgsfloatval_t *y = lbfgs_malloc(2);
        CHECK(y != NULL);
        y[0] = 0.0; y[1] = 0.0;
        lbfgs_parameter_init(&param);
        param.orthantwise_c = 1.0;
        param.linesearch = LBFGS_LINESEARCH_BACKTRACKING;
        ret = lbfgs(2, y, &fx, quadratic, NULL, NULL, &param);
        CHECK(ret == LBFGS_SUCCESS);
        CHECK(fabs(y[0] - 0.5) < 1e-4);
        CHECK(fabs(y[1] - 1.5) < 1e-4);
        lbfgs_free(y);
    }

    /* 4) 鸿蒙特有：错误路径健壮性。lib/lbfgs.c 在触碰 x 之前先做参数校验
     *    （n<=0 → LBFGSERR_INVALID_N，param.epsilon<0 → LBFGSERR_INVALID_EPSILON），
     *    断言 OHOS aarch64 上非法入参返回确定的负错误码，而不是崩溃或静默继续。
     *    上游 sample/sample.c 与第 1~3 组断言都不覆盖这些错误分支。 */
    lbfgs_parameter_init(&param);
    CHECK(lbfgs(0, NULL, &fx, quadratic, NULL, NULL, &param) == LBFGSERR_INVALID_N);
    param.epsilon = -1.0;
    {
        lbfgsfloatval_t *w = lbfgs_malloc(2);
        CHECK(w != NULL);
        w[0] = 0.0; w[1] = 0.0;
        CHECK(lbfgs(2, w, &fx, quadratic, NULL, NULL, &param)
              == LBFGSERR_INVALID_EPSILON);
        lbfgs_free(w);
    }

    if (failures) {
        printf("test_lbfgs: %d assertion(s) FAILED\n", failures);
        return 1;
    }
    printf("test_lbfgs: all assertions passed\n");
    return 0;
}
