/* test_librsb.c — consumer smoke test for the librsb package (R34).
 *
 * Exercises the real public API from <rsb.h> end to end, mirroring the
 * lifecycle of upstream examples/hello.c but with strict numeric checks:
 *   1. rsb_lib_init()
 *   2. rsb_mtx_alloc_from_coo_const() of a 3x3 diagonal double matrix
 *   3. rsb_spmv() y = A*x, verified element-wise
 *   4. rsb_spmv() with transposition flag, verified element-wise
 *   5. rsb_spmv() with beta accumulation (y = A*x + y), verified
 *   6. rsb_mtx_free() + rsb_lib_exit()
 *
 * Each passing stage prints exactly one "CHECK-OK:" line (6 total).
 * The conanfile.py test() counts those lines for the
 * HMBS_TEST_PACKAGE_RESULT machine-evidence marker (exit 0 alone is
 * not proof).
 */
#include <stdio.h>
#include <math.h>
#include <rsb.h>

#define NROWS 3
#define NCOLE 3
#define NDIAG 3

static int check_close(const char *name, double got, double want)
{
    if (fabs(got - want) > 1e-12) {
        printf("CHECK-FAIL: %s: got %g, want %g\n", name, got, want);
        return 1;
    }
    return 0;
}

int main(void)
{
    /* 3x3 diagonal matrix diag(2,3,4) in COO form */
    const rsb_coo_idx_t IA[NDIAG] = {0, 1, 2};
    const rsb_coo_idx_t JA[NDIAG] = {0, 1, 2};
    const double VA[NDIAG] = {2.0, 3.0, 4.0};
    double X[NROWS] = {1.0, 1.0, 1.0};
    double Y[NROWS] = {0.0, 0.0, 0.0};
    const double alpha = 1.0;
    const double beta0 = 0.0;
    const double beta1 = 1.0;
    const double want[NROWS] = {2.0, 3.0, 4.0};
    struct rsb_mtx_t *mtx = NULL;
    rsb_err_t err = RSB_ERR_NO_ERROR;
    rsb_int_t i;

    /* 1. library init */
    err = rsb_lib_init(RSB_NULL_INIT_OPTIONS);
    if (err != RSB_ERR_NO_ERROR) {
        printf("CHECK-FAIL: rsb_lib_init: err=%d\n", (int)err);
        return 1;
    }
    printf("CHECK-OK: rsb_lib_init\n");

    /* 2. matrix assembly from COO */
    mtx = rsb_mtx_alloc_from_coo_const(
        VA, IA, JA, NDIAG, RSB_NUMERICAL_TYPE_DOUBLE,
        NROWS, NCOLE, 1, 1, RSB_FLAG_NOFLAGS, &err);
    if (mtx == NULL || err != RSB_ERR_NO_ERROR) {
        printf("CHECK-FAIL: rsb_mtx_alloc_from_coo_const: err=%d\n",
            (int)err);
        return 1;
    }
    printf("CHECK-OK: rsb_mtx_alloc_from_coo_const (3x3 diag, double)\n");

    /* 3. y = A*x, no transposition */
    err = rsb_spmv(RSB_TRANSPOSITION_N, &alpha, mtx, X, 1,
        &beta0, Y, 1);
    if (err != RSB_ERR_NO_ERROR) {
        printf("CHECK-FAIL: rsb_spmv(N): err=%d\n", (int)err);
        rsb_mtx_free(mtx);
        return 1;
    }
    for (i = 0; i < NROWS; ++i) {
        if (check_close("spmv(N)", Y[i], want[i])) {
            rsb_mtx_free(mtx);
            return 1;
        }
    }
    printf("CHECK-OK: rsb_spmv(N) y={%g,%g,%g}\n", Y[0], Y[1], Y[2]);

    /* 4. y = A^T*x (diagonal matrix is symmetric: same result) */
    Y[0] = Y[1] = Y[2] = 0.0;
    err = rsb_spmv(RSB_TRANSPOSITION_T, &alpha, mtx, X, 1,
        &beta0, Y, 1);
    if (err != RSB_ERR_NO_ERROR) {
        printf("CHECK-FAIL: rsb_spmv(T): err=%d\n", (int)err);
        rsb_mtx_free(mtx);
        return 1;
    }
    for (i = 0; i < NROWS; ++i) {
        if (check_close("spmv(T)", Y[i], want[i])) {
            rsb_mtx_free(mtx);
            return 1;
        }
    }
    printf("CHECK-OK: rsb_spmv(T) y={%g,%g,%g}\n", Y[0], Y[1], Y[2]);

    /* 5. y = A*x + y with y preset to {1,1,1} */
    Y[0] = Y[1] = Y[2] = 1.0;
    err = rsb_spmv(RSB_TRANSPOSITION_N, &alpha, mtx, X, 1,
        &beta1, Y, 1);
    if (err != RSB_ERR_NO_ERROR) {
        printf("CHECK-FAIL: rsb_spmv(beta=1): err=%d\n", (int)err);
        rsb_mtx_free(mtx);
        return 1;
    }
    for (i = 0; i < NROWS; ++i) {
        if (check_close("spmv(beta=1)", Y[i], want[i] + 1.0)) {
            rsb_mtx_free(mtx);
            return 1;
        }
    }
    printf("CHECK-OK: rsb_spmv(beta=1) y={%g,%g,%g}\n",
        Y[0], Y[1], Y[2]);

    /* 6. teardown: free must return NULL, exit must succeed */
    if (rsb_mtx_free(mtx) != NULL) {
        printf("CHECK-FAIL: rsb_mtx_free did not return NULL\n");
        return 1;
    }
    err = rsb_lib_exit(RSB_NULL_EXIT_OPTIONS);
    if (err != RSB_ERR_NO_ERROR) {
        printf("CHECK-FAIL: rsb_lib_exit: err=%d\n", (int)err);
        return 1;
    }
    printf("CHECK-OK: rsb_mtx_free + rsb_lib_exit\n");
    return 0;
}
