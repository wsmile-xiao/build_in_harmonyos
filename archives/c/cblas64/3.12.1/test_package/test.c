#include <cblas.h>
#include <stdio.h>

/* 真实消费者：链接 libcblas64 + libblas64 + Fortran 运行时，调用 64 位整数索引
 * API（cblas_*_64，声明见 cblas_64.h）并逐项校验计算结果。列主序约定同上游。 */
int main(void) {
    /* level 1: cblas_ddot_64 = x·y = 1*4+2*5+3*6 = 32（N/incX/incY 均为 int64_t） */
    double x[3] = {1.0, 2.0, 3.0};
    double y[3] = {4.0, 5.0, 6.0};
    if (cblas_ddot_64(3, x, 1, y, 1) != 32.0) {
        puts("FAIL cblas_ddot_64");
        return 1;
    }
    /* level 1: cblas_dasum_64 = |1|+|2|+|3| = 6 */
    if (cblas_dasum_64(3, x, 1) != 6.0) {
        puts("FAIL cblas_dasum_64");
        return 1;
    }
    /* level 2: cblas_daxpy_64 y <- alpha*x + y = {6,9,12} */
    cblas_daxpy_64(3, 2.0, x, 1, y, 1);
    if (y[0] != 6.0 || y[1] != 9.0 || y[2] != 12.0) {
        puts("FAIL cblas_daxpy_64");
        return 1;
    }
    /* level 3: cblas_dgemm_64（列主序）C <- A*B，
     * A = [[1,2],[3,4]]，B = [[5,6],[7,8]]，C = [[19,22],[43,50]] */
    double a[4] = {1.0, 3.0, 2.0, 4.0};
    double b[4] = {5.0, 7.0, 6.0, 8.0};
    double c[4] = {0.0, 0.0, 0.0, 0.0};
    cblas_dgemm_64(CblasColMajor, CblasNoTrans, CblasNoTrans,
                   2, 2, 2, 1.0, a, 2, b, 2, 0.0, c, 2);
    if (c[0] != 19.0 || c[1] != 43.0 || c[2] != 22.0 || c[3] != 50.0) {
        puts("FAIL cblas_dgemm_64");
        return 1;
    }
    puts("cblas64 consumer OK: ddot_64/dasum_64/daxpy_64/dgemm_64 verified");
    return 0;
}
