#include <stdio.h>
#include <math.h>

/* 真实消费者：直接链接 libblas.a（参考 BLAS），调用 Fortran 符号
 * （LP64 尾下划线约定，flang 产物），逐项校验计算结果，而非仅解析符号。
 * 参考 BLAS 无头文件，符号按 Fortran ABI 外部声明。 */

/* level 1: ddot = x·y = 1*4+2*5+3*6 = 32 */
extern double ddot_(const int *n, const double *x, const int *incx,
                    const double *y, const int *incy);
/* level 1: dasum = |1|+|2|+|3| = 6 */
extern double dasum_(const int *n, const double *x, const int *incx);
/* level 2: daxpy y <- alpha*x + y = {6,9,12} */
extern void daxpy_(const int *n, const double *alpha, const double *x,
                   const int *incx, double *y, const int *incy);
/* level 3: dgemm（列主序）C <- A*B，A=[[1,2],[3,4]]，B=[[5,6],[7,8]] */
extern void dgemm_(const char *transa, const char *transb,
                   const int *m, const int *n, const int *k,
                   const double *alpha, const double *a, const int *lda,
                   const double *b, const int *ldb,
                   const double *beta, double *c, const int *ldc);

static int close_enough(double got, double want) {
    return fabs(got - want) < 1e-9;
}

int main(void) {
    int n3 = 3;
    int one = 1;
    double x[3] = {1.0, 2.0, 3.0};
    double y[3] = {4.0, 5.0, 6.0};

    /* level 1: ddot = 32 */
    if (!close_enough(ddot_(&n3, x, &one, y, &one), 32.0)) {
        puts("FAIL ddot");
        return 1;
    }
    /* level 1: dasum = 6 */
    if (!close_enough(dasum_(&n3, x, &one), 6.0)) {
        puts("FAIL dasum");
        return 1;
    }
    /* level 2: daxpy y <- 2*x + y = {6,9,12} */
    {
        double alpha = 2.0;
        double yy[3] = {4.0, 5.0, 6.0};
        daxpy_(&n3, &alpha, x, &one, yy, &one);
        if (!close_enough(yy[0], 6.0) || !close_enough(yy[1], 9.0)
                || !close_enough(yy[2], 12.0)) {
            puts("FAIL daxpy");
            return 1;
        }
    }
    /* level 3: dgemm（列主序）
     * A = [[1,2],[3,4]]（列主序 {1,3,2,4}），B = [[5,6],[7,8]]（列主序 {5,7,6,8}）
     * C = [[19,22],[43,50]]（列主序 {19,43,22,50}） */
    {
        int two = 2;
        double alpha = 1.0, beta = 0.0;
        double a[4] = {1.0, 3.0, 2.0, 4.0};
        double b[4] = {5.0, 7.0, 6.0, 8.0};
        double c[4] = {0.0, 0.0, 0.0, 0.0};
        char nt = 'N';
        dgemm_(&nt, &nt, &two, &two, &two,
               &alpha, a, &two, b, &two, &beta, c, &two);
        if (!close_enough(c[0], 19.0) || !close_enough(c[1], 43.0)
                || !close_enough(c[2], 22.0) || !close_enough(c[3], 50.0)) {
            puts("FAIL dgemm");
            return 1;
        }
    }
    puts("blas consumer OK: ddot/dasum/daxpy/dgemm verified");
    return 0;
}