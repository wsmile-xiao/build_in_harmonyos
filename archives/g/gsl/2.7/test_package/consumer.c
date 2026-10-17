/* GSL 2.7 HarmonyOS PC 鸿蒙消费者用例程序。
 *
 * rule12：鸿蒙特有测试必须是「具名端到端消费者用例」，不能是断言清单。
 *   本程序的每个 HC-n 都是一条完整端到端流程：
 *       构造真实输入 → 经 GSL 公开 API 计算 → 产出真实结果 → 与独立参考值比对
 *   R34：真实 #include 公共头 + 链接 -lgsl -lgslcblas -lm，不是只为打印而存在的空壳。
 *
 * stdout 约定（供 test_package/test.sh 用 POSIX 内置命令解析）：
 *   指定用例时：第一行 "<CASE> <VALUE> PASS|FAIL"，随后为人类可读明细。
 *   VALUE 是固定小数位的真实计算结果（千分位无空格），driver 逐字比对以校验内容。
 *   --all 时额外打印头尾注释行。
 */
#include <gsl/gsl_version.h>
#include <gsl/gsl_sf_bessel.h>
#include <gsl/gsl_matrix.h>
#include <gsl/gsl_vector.h>
#include <gsl/gsl_permutation.h>
#include <gsl/gsl_linalg.h>
#include <gsl/gsl_blas.h>
#include <gsl/gsl_rng.h>
#include <gsl/gsl_statistics_double.h>
#include <gsl/gsl_histogram.h>
#include <gsl/gsl_errno.h>

#include <math.h>
#include <stdio.h>
#include <string.h>

/* 打印一行机器可读裁决行 + 明细；返回 0 通过 / 1 失败。 */
static int report(const char *cid, const char *value, int ok,
                  const char *what, const char *ref)
{
    printf("%s %s %s\n", cid, value, ok ? "PASS" : "FAIL");
    printf("  what : %s\n", what);
    printf("  value: %s\n", value);
    printf("  ref  : %s\n", ref);
    return ok ? 0 : 1;
}

/* HC-1 特殊函数：贝塞尔 J0(5) 端到端求值 */
static int case_hc1(void)
{
    double v = gsl_sf_bessel_J0(5.0);
    char val[64];
    snprintf(val, sizeof(val), "%.6f", v);
    return report("HC-1", val,
                  fabs(v - (-0.177596771314338)) < 1e-13,
                  "gsl_sf_bessel_J0(5.0)",
                  "J0(5) = -0.177596771314338（Abramowitz & Stegun 9.4.1）");
}

/* HC-2 线性代数：LU 分解解 2x2 方程组（该路径会走 CBLAS 符号） */
static int case_hc2(void)
{
    double a[] = { 2.0, 1.0,       /* A = [[2,1],[1,3]] 行主序 */
                   1.0, 3.0 };
    double b[] = { 3.0, 5.0 };
    gsl_matrix_view m = gsl_matrix_view_array(a, 2, 2);
    gsl_vector_view bv = gsl_vector_view_array(b, 2);
    gsl_vector *x = gsl_vector_alloc(2);
    gsl_permutation *p = gsl_permutation_alloc(2);
    int signum = 0, ok;
    double x0, x1;
    char val[64];

    gsl_linalg_LU_decomp(&m.matrix, p, &signum);
    gsl_linalg_LU_solve(&m.matrix, p, &bv.vector, x);
    x0 = gsl_vector_get(x, 0);
    x1 = gsl_vector_get(x, 1);
    snprintf(val, sizeof(val), "%.6f,%.6f", x0, x1);
    ok = (fabs(x0 - 0.8) < 1e-12) && (fabs(x1 - 1.4) < 1e-12);

    gsl_vector_free(x);
    gsl_permutation_free(p);
    return report("HC-2", val, ok,
                  "gsl_linalg_LU_decomp + LU_solve（2x2 Ax=b）",
                  "2x+y=3, x+3y=5 → x = [0.800000, 1.400000]");
}

/* HC-3 随机数：mt19937 固定种子必须复现同一序列 */
static int case_hc3(void)
{
    gsl_rng *r = gsl_rng_alloc(gsl_rng_mt19937);
    unsigned long a, b, a2, b2;
    int ok;
    char val[64];

    gsl_rng_set(r, 42);
    a = gsl_rng_get(r);
    b = gsl_rng_get(r);
    gsl_rng_set(r, 42);           /* 同种子重放 */
    a2 = gsl_rng_get(r);
    b2 = gsl_rng_get(r);

    snprintf(val, sizeof(val), "%lu,%lu", a, b);
    ok = (a == a2) && (b == b2) && (strcmp(gsl_rng_name(r), "mt19937") == 0);
    gsl_rng_free(r);
    return report("HC-3", val, ok,
                  "gsl_rng_mt19937 同种子两次取序列",
                  "mt19937 为确定性整数算法：seed=42 前两值可复现");
}

/* HC-4 统计：对真实样本求均值与总体标准差 */
static int case_hc4(void)
{
    double d[] = { 2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0 };
    double mean = gsl_stats_mean(d, 1, 8);
    double sd = gsl_stats_sd_with_fixed_mean(d, 1, 8, mean);
    int ok;
    char val[64];

    snprintf(val, sizeof(val), "%.6f,%.6f", mean, sd);
    ok = (fabs(mean - 5.0) < 1e-12) && (fabs(sd - 2.0) < 1e-12);
    return report("HC-4", val, ok,
                  "gsl_stats_mean + gsl_stats_sd_with_fixed_mean（n=8）",
                  "样本均值 5.0；总体标准差 2.0（手算可验）");
}

/* HC-5 BLAS：dgemm 2x2 矩阵乘法（证明 libgslcblas 对消费者可用） */
static int case_hc5(void)
{
    double A[] = { 1.0, 2.0, 3.0, 4.0 };   /* [[1,2],[3,4]] */
    double B[] = { 5.0, 6.0, 7.0, 8.0 };   /* [[5,6],[7,8]] */
    double C[] = { 0.0, 0.0, 0.0, 0.0 };
    gsl_matrix_view av = gsl_matrix_view_array(A, 2, 2);
    gsl_matrix_view bv = gsl_matrix_view_array(B, 2, 2);
    gsl_matrix_view cv = gsl_matrix_view_array(C, 2, 2);
    int ok = 1;
    char val[160];

    gsl_blas_dgemm(CblasNoTrans, CblasNoTrans, 1.0,
                   &av.matrix, &bv.matrix, 0.0, &cv.matrix);

    ok = ok && (fabs(C[0] - 19.0) < 1e-12) && (fabs(C[1] - 22.0) < 1e-12);
    ok = ok && (fabs(C[2] - 43.0) < 1e-12) && (fabs(C[3] - 50.0) < 1e-12);
    snprintf(val, sizeof(val), "%.6f,%.6f,%.6f,%.6f", C[0], C[1], C[2], C[3]);
    return report("HC-5", val, ok,
                  "gsl_blas_dgemm(CblasNoTrans, CblasNoTrans, 2x2)",
                  "[[1,2],[3,4]] x [[5,6],[7,8]] = [[19,22],[43,50]]");
}

/* HC-6 直方图：分箱计数端到端（含越界样本丢弃） */
static int case_hc6(void)
{
    double data[] = { 0.5, 0.5, 1.5, 2.5, 2.5, 2.5, 3.5, 9.9 };
    gsl_histogram *h = gsl_histogram_alloc(4);
    size_t i, n = sizeof(data) / sizeof(data[0]);
    size_t dropped = 0, sum = 0;
    int ok;
    char val[64];

    gsl_histogram_set_ranges_uniform(h, 0.0, 4.0);
    for (i = 0; i < n; ++i)
        if (gsl_histogram_increment(h, data[i]) == GSL_EDOM)
            dropped++;

    snprintf(val, sizeof(val), "%g,%g,%g,%g",
             gsl_histogram_get(h, 0), gsl_histogram_get(h, 1),
             gsl_histogram_get(h, 2), gsl_histogram_get(h, 3));
    for (i = 0; i < 4; ++i) sum += (size_t) gsl_histogram_get(h, i);

    ok = (gsl_histogram_get(h, 0) == 2.0) && (gsl_histogram_get(h, 1) == 1.0)
      && (gsl_histogram_get(h, 2) == 3.0) && (gsl_histogram_get(h, 3) == 1.0)
      && (sum == 7) && (dropped == 1);
    gsl_histogram_free(h);
    return report("HC-6", val, ok,
                  "gsl_histogram 4 箱 [0,4) 填充 8 个样本",
                  "[0,1)=2 [1,2)=1 [2,3)=3 [3,4)=1；9.9 越界丢弃（合计 7）");
}

typedef struct { const char *id; int (*fn)(void); } hc_case;

int main(int argc, char **argv)
{
    static const hc_case cases[] = {
        { "HC-1", case_hc1 }, { "HC-2", case_hc2 }, { "HC-3", case_hc3 },
        { "HC-4", case_hc4 }, { "HC-5", case_hc5 }, { "HC-6", case_hc6 },
    };
    const char *want = (argc > 1) ? argv[1] : "--all";
    int all = (strcmp(want, "--all") == 0);
    int fails = 0;
    size_t i;

    if (all)
        printf("# gsl consumer cases, libgsl %s, cases=%zu\n",
               GSL_VERSION, sizeof(cases) / sizeof(cases[0]));

    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i)
        if (all || strcmp(want, cases[i].id) == 0)
            fails += cases[i].fn();

    if (all)
        printf("# cases failed: %d\n", fails);
    return fails ? 1 : 0;
}
