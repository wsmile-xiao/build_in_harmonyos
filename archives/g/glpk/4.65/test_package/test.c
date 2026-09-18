/* GLPK 5.0 鸿蒙 PC 适配验证。
 * R34：直接 #include <glpk.h> 并链接 libglpk，**真解一个线性规划**并校验最优值。 */
#include <glpk.h>

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
    printf("GLPK %s\n\n", glp_version());

    /* 经典 LP（GLPK 官方文档例题）：
         max  10x1 + 6x2 + 4x3
         s.t.  x1 +  x2 +  x3 <= 100
              10x1 + 4x2 + 5x3 <= 600
               2x1 + 2x2 + 6x3 <= 300
              x >= 0
       已知最优解 z = 733.333333，x = (33.3333, 66.6667, 0) */
    glp_prob *lp = glp_create_prob();
    check(lp != NULL, "glp_create_prob", NULL);
    if (!lp) return 1;

    glp_set_obj_dir(lp, GLP_MAX);
    glp_add_rows(lp, 3);
    glp_set_row_bnds(lp, 1, GLP_UP, 0.0, 100.0);
    glp_set_row_bnds(lp, 2, GLP_UP, 0.0, 600.0);
    glp_set_row_bnds(lp, 3, GLP_UP, 0.0, 300.0);

    glp_add_cols(lp, 3);
    for (int j = 1; j <= 3; j++) glp_set_col_bnds(lp, j, GLP_LO, 0.0, 0.0);
    glp_set_obj_coef(lp, 1, 10.0);
    glp_set_obj_coef(lp, 2, 6.0);
    glp_set_obj_coef(lp, 3, 4.0);

    int ia[1+9], ja[1+9];
    double ar[1+9];
    int k = 0;
    double A[3][3] = {{1,1,1},{10,4,5},{2,2,6}};
    for (int i = 1; i <= 3; i++)
        for (int j = 1; j <= 3; j++) { k++; ia[k]=i; ja[k]=j; ar[k]=A[i-1][j-1]; }
    glp_load_matrix(lp, 9, ia, ja, ar);
    check(glp_get_num_rows(lp) == 3 && glp_get_num_cols(lp) == 3,
          "构建 3x3 约束矩阵", NULL);

    glp_smcp parm;
    glp_init_smcp(&parm);
    parm.msg_lev = GLP_MSG_ERR;          /* 静默，只报错误 */
    int rc = glp_simplex(lp, &parm);
    check(rc == 0, "glp_simplex 求解返回 0", NULL);

    int st = glp_get_status(lp);
    check(st == GLP_OPT, "解状态为最优（GLP_OPT）", NULL);

    double z  = glp_get_obj_val(lp);
    double x1 = glp_get_col_prim(lp, 1);
    double x2 = glp_get_col_prim(lp, 2);
    double x3 = glp_get_col_prim(lp, 3);
    snprintf(buf, sizeof(buf), "z=%.6f 期望 733.333333；x=(%.4f, %.4f, %.4f) 期望 (33.3333, 66.6667, 0)",
             z, x1, x2, x3);
    check(fabs(z - 733.333333333) < 1e-6 &&
          fabs(x1 - 100.0/3.0) < 1e-6 && fabs(x2 - 200.0/3.0) < 1e-6 && fabs(x3) < 1e-9,
          "最优值与最优解均与已知答案一致", buf);

    glp_delete_prob(lp);
    printf("\n%s：%d 项断言，%d 项失败\n",
           g_failed ? "结论 FAIL" : "结论 PASS", g_total, g_failed);
    return g_failed ? 1 : 0;
}
