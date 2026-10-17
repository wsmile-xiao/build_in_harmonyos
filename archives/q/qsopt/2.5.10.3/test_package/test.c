/*
 * test.c — QSopt_ex consumer test (HarmonyOS / macOS / Linux)
 *
 * Loads the upstream test LP and solves it with the exact rational solver:
 *     Maximize  3x + 2y + 4z
 *     s.t.      3x + 2y +  z <= 12
 *               5x +  y       = 10
 *               x >= 2, y free, 1 <= z <= 10
 * Asserts the solver returns QS_LP_OPTIMAL and the exact optimum equals
 * 42 (= 42/1). Mirrors upstream tests/test_qs.c (make check) — R51.
 */
#include <stdio.h>
#include <stdlib.h>
#include <gmp.h>
#include <qsopt_ex/QSopt_ex.h>

int main(void)
{
    int rval = 0, status = 0, nrows = 0, ncols = 0, i;
    mpq_t value;
    mpq_t *x = (mpq_t *) NULL;
    mpq_QSprob p = (mpq_QSprob) NULL;

    int cmatcnt[3] = { 2, 2, 1 };
    int cmatbeg[3] = { 0, 2, 4 };
    int cmatind[5] = { 0, 1, 0, 1, 0 };
    char sense[2] = { 'L', 'E' };
    const char *colnames[3] = { "x", "y", "z" };
    const char *rownames[2] = { "c1", "c2" };
    mpq_t cmatval[5], obj[3], rhs[2], lower[3], upper[3];

    QSexactStart();
    mpq_init(value);
    /* Must be called before any other QS function. */
    QSexact_set_precision(128);

    for (i = 0; i < 5; i++) mpq_init(cmatval[i]);
    mpq_set_d(cmatval[0], 3.0);
    mpq_set_d(cmatval[1], 5.0);
    mpq_set_d(cmatval[2], 2.0);
    mpq_set_d(cmatval[3], 1.0);
    mpq_set_d(cmatval[4], 1.0);
    for (i = 0; i < 3; i++) mpq_init(obj[i]);
    mpq_set_d(obj[0], 3.0);
    mpq_set_d(obj[1], 2.0);
    mpq_set_d(obj[2], 4.0);
    for (i = 0; i < 2; i++) mpq_init(rhs[i]);
    mpq_set_d(rhs[0], 12.0);
    mpq_set_d(rhs[1], 10.0);
    for (i = 0; i < 3; i++) mpq_init(lower[i]);
    mpq_set_d(lower[0], 2.0);
    mpq_set(lower[1], mpq_ILL_MINDOUBLE);
    mpq_set_d(lower[2], 1.0);
    for (i = 0; i < 3; i++) mpq_init(upper[i]);
    mpq_set(upper[0], mpq_ILL_MAXDOUBLE);
    mpq_set(upper[1], mpq_ILL_MAXDOUBLE);
    mpq_set_d(upper[2], 10.0);

    p = mpq_QSload_prob("small", 3, 2, cmatcnt, cmatbeg, cmatind, cmatval,
                        QS_MAX, obj, rhs, sense, lower, upper, colnames,
                        rownames);
    if (p == (mpq_QSprob) NULL) {
        fprintf(stderr, "FAIL: unable to load LP\n");
        rval = 1;
        goto CLEANUP;
    }

    nrows = mpq_QSget_rowcount(p);
    ncols = mpq_QSget_colcount(p);
    if (nrows != 2 || ncols != 3) {
        fprintf(stderr, "FAIL: row/col count %d/%d (expected 2/3)\n", nrows, ncols);
        rval = 1;
        goto CLEANUP;
    }

    rval = QSexact_solver(p, NULL, NULL, NULL, DUAL_SIMPLEX, &status);
    if (rval != 0 || status != QS_LP_OPTIMAL) {
        fprintf(stderr, "FAIL: solve rc=%d status=%d (expected QS_LP_OPTIMAL)\n",
                rval, status);
        rval = 1;
        goto CLEANUP;
    }

    rval = mpq_QSget_objval(p, &value);
    if (rval != 0 || mpq_cmp_ui(value, 42, 1) != 0) {
        fprintf(stderr, "FAIL: objval rc=%d value=%s (expected exactly 42)\n",
                rval, mpq_get_str(NULL, 10, value));
        rval = 1;
        goto CLEANUP;
    }

    x = (mpq_t *) malloc(ncols * sizeof(mpq_t));
    for (i = 0; i < ncols; i++) mpq_init(x[i]);
    rval = mpq_QSget_x_array(p, x);
    if (rval != 0) {
        fprintf(stderr, "FAIL: x-array rc=%d\n", rval);
        rval = 1;
        goto CLEANUP;
    }

    printf("PASS: exact optimum = %s (x=%s, y=%s, z=%s)\n",
           mpq_get_str(NULL, 10, value),
           mpq_get_str(NULL, 10, x[0]),
           mpq_get_str(NULL, 10, x[1]),
           mpq_get_str(NULL, 10, x[2]));

CLEANUP:
    if (p) mpq_QSfree_prob(p);
    mpq_clear(value);
    for (i = 0; i < 5; i++) mpq_clear(cmatval[i]);
    for (i = 0; i < 3; i++) mpq_clear(obj[i]);
    for (i = 0; i < 2; i++) mpq_clear(rhs[i]);
    for (i = 0; i < 3; i++) mpq_clear(lower[i]);
    for (i = 0; i < 3; i++) mpq_clear(upper[i]);
    if (x) {
        for (i = 0; i < ncols; i++) mpq_clear(x[i]);
        free(x);
    }
    QSexactClear();
    return rval;
}
