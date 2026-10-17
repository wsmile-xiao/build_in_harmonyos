/* glpk 4.65.1 消费者用例：oldapi/lpx 兼容层验证（模拟 COIN-OR OsiGlpk 上层）。
 * R34：只通过已安装/导出的公开头文件（lpx.h → glpk.h）与公开链接目标
 * （-lglpk -llpx）使用本库，调用旧 API lpx_* 真解一个线性规划并校验结果。 */
#include <lpx.h>

#include <math.h>
#include <stdio.h>

static int g_failed = 0, g_total = 0;
static void check(int ok, const char *what, const char *detail) {
    g_total++;
    printf("  [%s] %s%s%s\n", ok ? "ok" : "FAIL", what,
           (detail && detail[0]) ? " — " : "", detail ? detail : "");
    if (!ok) g_failed++;
}

int main(void) {
    char buf[224];
    printf("GLPK %s (oldapi/lpx compat)\n\n", glp_version());

    /* 经典 LP（GLPK 官方文档例题）：
         max  10x1 + 6x2 + 4x3
         s.t.  x1 +  x2 +  x3 <= 100
              10x1 + 4x2 + 5x3 <= 600
               2x1 + 2x2 + 6x3 <= 300
              x >= 0
       已知最优解 z = 733.333333，x = (33.3333, 66.6667, 0) */
    LPX *lp = lpx_create_prob();
    check(lp != NULL, "lpx_create_prob", NULL);
    if (!lp) return 1;

    lpx_set_obj_dir(lp, LPX_MAX);
    lpx_add_rows(lp, 3);
    lpx_set_row_bnds(lp, 1, LPX_UP, 0.0, 100.0);
    lpx_set_row_bnds(lp, 2, LPX_UP, 0.0, 600.0);
    lpx_set_row_bnds(lp, 3, LPX_UP, 0.0, 300.0);

    lpx_add_cols(lp, 3);
    for (int j = 1; j <= 3; j++) lpx_set_col_bnds(lp, j, LPX_LO, 0.0, 0.0);
    lpx_set_obj_coef(lp, 1, 10.0);
    lpx_set_obj_coef(lp, 2, 6.0);
    lpx_set_obj_coef(lp, 3, 4.0);

    int ia[1+9], ja[1+9];
    double ar[1+9];
    int k = 0;
    double A[3][3] = {{1,1,1},{10,4,5},{2,2,6}};
    for (int i = 1; i <= 3; i++)
        for (int j = 1; j <= 3; j++) { k++; ia[k]=i; ja[k]=j; ar[k]=A[i-1][j-1]; }
    lpx_load_matrix(lp, 9, ia, ja, ar);
    check(lpx_get_num_rows(lp) == 3 && lpx_get_num_cols(lp) == 3,
          "lpx_load_matrix 构建 3x3 约束矩阵", NULL);

    lpx_set_int_parm(lp, LPX_K_MSGLEV, 0);   /* 静默求解 */
    /* 官方 oldapi 语义：成功返回 LPX_E_OK（200），非 0 但恒等常量 */
    int rc = lpx_simplex(lp);
    check(rc == LPX_E_OK, "lpx_simplex 求解返回 LPX_E_OK", NULL);

    int st = lpx_get_status(lp);
    check(st == LPX_OPT, "解状态为最优（LPX_OPT）", NULL);

    double z  = lpx_get_obj_val(lp);
    double x1 = lpx_get_col_prim(lp, 1);
    double x2 = lpx_get_col_prim(lp, 2);
    double x3 = lpx_get_col_prim(lp, 3);
    snprintf(buf, sizeof(buf), "z=%.6f 期望 733.333333；x=(%.4f, %.4f, %.4f) 期望 (33.3333, 66.6667, 0)",
             z, x1, x2, x3);
    check(fabs(z - 733.333333333) < 1e-6 &&
          fabs(x1 - 100.0/3.0) < 1e-6 && fabs(x2 - 200.0/3.0) < 1e-6 && fabs(x3) < 1e-9,
          "最优值与最优解均与已知答案一致", buf);

    /* LPXKKT 校验（lpx_check_kkt，scaled=0 未缩放解）：KKT.PE/PB 误差应为 0 */
    LPXKKT kkt;
    lpx_check_kkt(lp, 0, &kkt);
    check(kkt.pe_ae_max < 1e-7 && kkt.pb_ae_max < 1e-7, "lpx_check_kkt 原始/界可行性误差≈0",
          buf + snprintf(buf, sizeof(buf), "pe_ae_max=%.3e pb_ae_max=%.3e",
                         kkt.pe_ae_max, kkt.pb_ae_max));

    lpx_delete_prob(lp);
    printf("\n%s：%d 项断言，%d 项失败\n",
           g_failed ? "结论 FAIL" : "结论 PASS", g_total, g_failed);
    return g_failed ? 1 : 0;
}
