/*
 * qsopt-ex test_package 消费者测试（6 断言）。
 *
 * 仅通过公开头 <qsopt_ex/QSopt_ex.h> 与公开 API 使用本库：加载与
 * test_package 样例同构的 2 变量 LP，精确（有理）求解，断言最优值 14 与
 * 解 (x=1, y=4) —— 与 test_ohos_solve.sh 用 esolver CLI 解同一问题的结果
 * 交叉互证。断言逐条以 TAP 风格打印，任一失败以非零退出。
 */
#include <stdio.h>
#include <stdlib.h>

#include <gmp.h>

#include <qsopt_ex/QSopt_ex.h>

static int checks = 0;
static int failures = 0;

static void
ck (int cond, const char *msg)
{
    if (cond)
        printf ("ok %d - %s\n", ++checks, msg);
    else
    {
        printf ("not ok %d - %s\n", ++checks, msg);
        failures++;
    }
}

int
main (void)
{
    mpq_QSprob p = (mpq_QSprob) NULL;
    mpq_t cmatval[4], obj[2], rhs[3], lower[2], upper[2], value;
    mpq_t *x = (mpq_t *) NULL;
    int i, rval = 0, status = 0, nrows, ncols;
    /* maximize 2x + 3y  s.t.  x + y <= 5, x <= 2, y <= 4, x,y >= 0
     * unique optimum: x=1, y=4, objective = 14                          */
    int cmatcnt[2] = { 2, 2 };            /* 每列非零元个数      */
    int cmatbeg[2] = { 0, 2 };            /* 每列起始下标        */
    int cmatind[4] = { 0, 1, 0, 2 };      /* 行下标: x->c1,c2; y->c1,c3 */
    char sense[3] = { 'L', 'L', 'L' };
    const char *colnames[2] = { "x", "y" };
    const char *rownames[3] = { "c1", "c2", "c3" };

    QSexactStart ();
    mpq_init (value);
    /* Must call QSexact_set_precision before using mpq_ILL_MAXDOUBLE. */
    QSexact_set_precision (128);

    for (i = 0; i < 4; i++)
        mpq_init (cmatval[i]);
    for (i = 0; i < 4; i++)
        mpq_set_d (cmatval[i], 1.0);
    for (i = 0; i < 2; i++)
        mpq_init (obj[i]);
    mpq_set_d (obj[0], 2.0);
    mpq_set_d (obj[1], 3.0);
    for (i = 0; i < 3; i++)
        mpq_init (rhs[i]);
    mpq_set_d (rhs[0], 5.0);
    mpq_set_d (rhs[1], 2.0);
    mpq_set_d (rhs[2], 4.0);
    for (i = 0; i < 2; i++)
    {
        mpq_init (lower[i]);
        mpq_init (upper[i]);
        mpq_set_d (lower[i], 0.0);
        mpq_set (upper[i], mpq_ILL_MAXDOUBLE);
    }

    p = mpq_QSload_prob ("ohos_sample", 2, 3, cmatcnt, cmatbeg, cmatind,
                         cmatval, QS_MAX, obj, rhs, sense, lower, upper,
                         colnames, rownames);
    ck (p != (mpq_QSprob) NULL, "load LP via mpq_QSload_prob (2 vars x 3 rows)");
    if (p == (mpq_QSprob) NULL)
        goto DONE;

    nrows = mpq_QSget_rowcount (p);
    ncols = mpq_QSget_colcount (p);
    ck (nrows == 3, "row count == 3");
    ck (ncols == 2, "col count == 2");

    rval = QSexact_solver (p, NULL, NULL, NULL, DUAL_SIMPLEX, &status);
    ck (rval == 0 && status == QS_LP_OPTIMAL, "QSexact_solver reaches QS_LP_OPTIMAL");

    rval = mpq_QSget_objval (p, &value);
    ck (rval == 0 && mpq_cmp_ui (value, 14, 1) == 0,
        "exact objective value == 14");

    x = (mpq_t *) malloc (ncols * sizeof (mpq_t));
    for (i = 0; i < ncols; i++)
        mpq_init (x[i]);
    rval = mpq_QSget_x_array (p, x);
    ck (rval == 0 && mpq_cmp_ui (x[0], 1, 1) == 0 && mpq_cmp_ui (x[1], 4, 1) == 0,
        "optimal solution x == (1, 4)");

DONE:
    printf ("consumer assertions: %d total, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
