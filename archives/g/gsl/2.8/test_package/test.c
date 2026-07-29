/* GSL 2.8 鸿蒙 PC 适配验证。
 * R34：直接 #include 并链接 -lgsl -lgslcblas，做**真实计算并校验数值**。
 *
 * 注意必须同时链 gslcblas：libgsl.so 把 CBLAS 符号留给消费方解析
 * （单独 dlopen libgsl.so 会报 cblas_sdsdot: symbol not found）——
 * 这也是本测试从 dlopen 探针改为直接链接的直接原因。
 */
#include <gsl/gsl_version.h>
#include <gsl/gsl_sf_bessel.h>
#include <gsl/gsl_matrix.h>
#include <gsl/gsl_linalg.h>
#include <gsl/gsl_rng.h>
#include <gsl/gsl_statistics_double.h>
#include <gsl/gsl_errno.h>

#include <math.h>
#include <stdio.h>
#include <string.h>

static int g_failed = 0, g_total = 0;
static void check(int ok, const char *what, const char *detail) {
    g_total++;
    printf("  [%s] %s%s%s\n", ok ? "ok" : "FAIL", what,
           (detail && detail[0]) ? " — " : "", detail ? detail : "");
    if (!ok) g_failed++;
}

int main(void) {
    char buf[192];
    printf("GSL %s\n\n", GSL_VERSION);

    /* ① 特殊函数：J0(5) 的已知值 -0.17759677131433830434739701 */
    {
        double v = gsl_sf_bessel_J0(5.0);
        snprintf(buf, sizeof(buf), "J0(5)=%.15f 期望 -0.177596771314338", v);
        check(fabs(v - (-0.1775967713143383)) < 1e-13, "sf: 贝塞尔函数 J0(5)", buf);
    }

    /* ② 线性代数：LU 分解解 Ax=b（该路径会调用 CBLAS）*/
    {
        double a_data[] = { 2.0, 1.0,
                            1.0, 3.0 };
        double b_data[] = { 3.0, 5.0 };
        gsl_matrix_view m = gsl_matrix_view_array(a_data, 2, 2);
        gsl_vector_view b = gsl_vector_view_array(b_data, 2);
        gsl_vector *x = gsl_vector_alloc(2);
        gsl_permutation *p = gsl_permutation_alloc(2);
        int s;
        gsl_linalg_LU_decomp(&m.matrix, p, &s);
        gsl_linalg_LU_solve(&m.matrix, p, &b.vector, x);
        double x0 = gsl_vector_get(x, 0), x1 = gsl_vector_get(x, 1);
        snprintf(buf, sizeof(buf), "x=[%.6f %.6f] 期望 [0.800000 1.400000]", x0, x1);
        check(fabs(x0 - 0.8) < 1e-12 && fabs(x1 - 1.4) < 1e-12,
              "linalg: LU 分解解方程组", buf);
        gsl_permutation_free(p);
        gsl_vector_free(x);
    }

    /* ③ 随机数发生器：固定种子必须复现固定序列 */
    {
        gsl_rng *r = gsl_rng_alloc(gsl_rng_mt19937);
        gsl_rng_set(r, 42);
        unsigned long a = gsl_rng_get(r);
        gsl_rng_set(r, 42);
        unsigned long b = gsl_rng_get(r);
        snprintf(buf, sizeof(buf), "同种子两次取值 %lu / %lu，name=%s", a, b, gsl_rng_name(r));
        check(a == b && strcmp(gsl_rng_name(r), "mt19937") == 0,
              "rng: mt19937 固定种子可复现", buf);
        gsl_rng_free(r);
    }

    /* ④ 统计：均值与标准差 */
    {
        double d[] = {2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0};
        double mean = gsl_stats_mean(d, 1, 8);
        double sd   = gsl_stats_sd_with_fixed_mean(d, 1, 8, mean);
        snprintf(buf, sizeof(buf), "mean=%.4f 期望 5.0；sd=%.4f 期望 2.0", mean, sd);
        check(fabs(mean - 5.0) < 1e-12 && fabs(sd - 2.0) < 1e-12,
              "statistics: 均值与总体标准差", buf);
    }

    printf("\n%s：%d 项断言，%d 项失败\n",
           g_failed ? "结论 FAIL" : "结论 PASS", g_total, g_failed);
    return g_failed ? 1 : 0;
}
