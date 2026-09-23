#include <cblas.h>
#include <stdio.h>

/* 真实消费者：链接 libcblas + openblas，调用 level1/2/3 公开 API 并逐项校验
 * 计算结果（对照手算值），而非仅解析符号。列主序约定与上游 CBLAS 文档一致。 */
int main(void) {
    /* level 1: ddot = x·y = 1*4+2*5+3*6 = 32 */
    double x[3] = {1.0, 2.0, 3.0};
    double y[3] = {4.0, 5.0, 6.0};
    if (cblas_ddot(3, x, 1, y, 1) != 32.0) {
        puts("FAIL cblas_ddot");
        return 1;
    }
    /* level 1: dasum = |1|+|2|+|3| = 6 */
    if (cblas_dasum(3, x, 1) != 6.0) {
        puts("FAIL cblas_dasum");
        return 1;
    }
    /* level 2: daxpy y <- alpha*x + y = {6,9,12} */
    cblas_daxpy(3, 2.0, x, 1, y, 1);
    if (y[0] != 6.0 || y[1] != 9.0 || y[2] != 12.0) {
        puts("FAIL cblas_daxpy");
        return 1;
    }
    /* level 3: dgemm（列主序）C <- A*B，
     * A = [[1,2],[3,4]]（列主序 {1,3,2,4}），B = [[5,6],[7,8]]（列主序 {5,7,6,8}），
     * C = [[19,22],[43,50]]（列主序 {19,43,22,50}） */
    double a[4] = {1.0, 3.0, 2.0, 4.0};
    double b[4] = {5.0, 7.0, 6.0, 8.0};
    double c[4] = {0.0, 0.0, 0.0, 0.0};
    cblas_dgemm(CblasColMajor, CblasNoTrans, CblasNoTrans,
                2, 2, 2, 1.0, a, 2, b, 2, 0.0, c, 2);
    if (c[0] != 19.0 || c[1] != 43.0 || c[2] != 22.0 || c[3] != 50.0) {
        puts("FAIL cblas_dgemm");
        return 1;
    }
    puts("cblas consumer OK: ddot/dasum/daxpy/dgemm verified");
    return 0;
}
