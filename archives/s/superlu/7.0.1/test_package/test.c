/* Real SuperLU API test: solve a small sparse linear system A*x=b with dgssv.
 * Matrix (4x4, CSC):
 *   A = [ 1  0  2  0 ]
 *       [ 0  3  0  0 ]
 *       [ 0  4  5  0 ]
 *       [ 6  0  0  7 ]
 * Exact solution: x = [1, 2, 3, 4], b = A*x = [7, 6, 23, 34].
 */
#include <math.h>
#include <stdio.h>
#include "slu_ddefs.h"

int main(void)
{
    SuperMatrix A, L, U, B;
    superlu_options_t options;
    SuperLUStat_t stat;
    int info;
    int m = 4, n = 4;
    int_t nnz = 7;
    int perm_c[4], perm_r[4];
    double *sol;

    /* CSC: col 0 rows {0,3}; col 1 rows {1,2}; col 2 rows {0,2}; col 3 row {3} */
    double a[]    = {1.0, 6.0, 3.0, 4.0, 2.0, 5.0, 7.0};
    int    asub[] = {0, 3, 1, 2, 0, 2, 3};
    int    xa[]   = {0, 2, 4, 6, 7};

    double rhs[] = {7.0, 6.0, 23.0, 34.0};

    dCreate_CompCol_Matrix(&A, m, n, nnz, a, asub, xa, SLU_NC, SLU_D, SLU_GE);
    dCreate_Dense_Matrix(&B, m, 1, rhs, m, SLU_DN, SLU_D, SLU_GE);

    set_default_options(&options);
    StatInit(&stat);

    dgssv(&options, &A, perm_c, perm_r, &L, &U, &B, &stat, &info);
    if (info != 0) {
        printf("dgssv failed with info=%d\n", (int)info);
        StatFree(&stat);
        return 1;
    }

    sol = (double *)((DNformat *)B.Store)->nzval;
    printf("solution: %.6f %.6f %.6f %.6f\n", sol[0], sol[1], sol[2], sol[3]);

    double err = fabs(sol[0] - 1.0) + fabs(sol[1] - 2.0)
               + fabs(sol[2] - 3.0) + fabs(sol[3] - 4.0);
    StatFree(&stat);

    if (err > 1e-8) {
        printf("solution check FAILED, err=%g\n", err);
        return 1;
    }
    printf("superlu 7.0.1 dgssv sparse solve: OK\n");
    return 0;
}
