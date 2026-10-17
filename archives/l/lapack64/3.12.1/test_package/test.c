#include <stdint.h>
#include <stdio.h>

/* 真实消费者：链接 liblapack64（ILP64 Fortran 符号）+ 全部传递依赖
 *（cblas64 的 libblas64 + Fortran 运行时），以 64 位整数参数调用 LAPACK
 * 例程并逐项对照手算值校验。列主序约定同上游。 */

extern void dgemm_(const char *transa, const char *transb,
                   const int64_t *m, const int64_t *n, const int64_t *k,
                   const double *alpha, const double *A, const int64_t *lda,
                   const double *B, const int64_t *ldb,
                   const double *beta, double *C, const int64_t *ldc);

extern void dgesv_(const int64_t *n, const int64_t *nrhs, double *A,
                   const int64_t *lda, int64_t *ipiv, double *b,
                   const int64_t *ldb, int64_t *info);

int main(void) {
    /* dgemm: C = A*B（Fortran 列主序）
       A = [[1,3],[2,4]], B = [[5,7],[6,8]] (列主序存储)
       -> C = A*B = [[23,31],[34,46]]，故 C[0]=23, C[3]=46 */
    char no = 'N';
    int64_t n = 2, lda = 2, ldb = 2, ldc = 2;
    double alpha = 1.0, beta = 0.0;
    double A[4] = {1.0, 2.0, 3.0, 4.0};
    double B[4] = {5.0, 6.0, 7.0, 8.0};
    double C[4] = {0, 0, 0, 0};
    dgemm_(&no, &no, &n, &n, &n, &alpha, A, &lda, B, &ldb, &beta, C, &ldc);
    if (C[0] != 23.0 || C[3] != 46.0) {
        printf("FAIL: dgemm C[0]=%.1f C[3]=%.1f\n", C[0], C[3]);
        return 1;
    }
    printf("PASS: dgemm\n");

    /* dgesv: A x = b, A = [[2,1],[1,3]] (对称, 列主序存储同), b = [3,7]
       解: 2x1+x2=3, x1+3x2=7 -> x1=0.4, x2=2.2 */
    int64_t n2 = 2, nrhs = 1, info = -1;
    int64_t ipiv[2];
    double A2[4] = {2.0, 1.0, 1.0, 3.0};
    double b2[2] = {3.0, 7.0};
    dgesv_(&n2, &nrhs, A2, &n2, ipiv, b2, &n2, &info);
    if (info != 0 || b2[0] < 0.39 || b2[0] > 0.41 ||
        b2[1] < 2.19 || b2[1] > 2.21) {
        printf("FAIL: dgesv info=%lld x=[%.2f, %.2f]\n",
               (long long)info, b2[0], b2[1]);
        return 1;
    }
    printf("PASS: dgesv\n");
    printf("lapack64 consumer OK: dgemm/dgesv verified (int64 args)\n");
    return 0;
}
