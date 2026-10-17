/* 真实断言：对一个秩亏的整数矩阵求零空间，维数可手算。 */
#include <stdio.h>
#include <stdlib.h>
#include <gmp.h>
#include <iml.h>

int main(void) {
    /* A = [[1,2],[2,4]]：两行成比例，秩=1，2 列 → 零空间维数 = 1 */
    long m = 2, n = 2;
    mpz_t *A = (mpz_t *)malloc(sizeof(mpz_t) * m * n);
    long v[4] = {1, 2, 2, 4};
    for (long i = 0; i < m * n; i++) { mpz_init(A[i]); mpz_set_si(A[i], v[i]); }
    mpz_t *N = NULL;
    long dim = nullspaceMP(m, n, A, &N);
    if (dim != 1) { fprintf(stderr, "零空间维数应为 1，实得 %ld\n", dim); return 1; }
    /* 校验 A*N == 0（真实计算，不只看维数） */
    for (long i = 0; i < m; i++) {
        mpz_t acc, t; mpz_init(acc); mpz_init(t);
        for (long j = 0; j < n; j++) { mpz_mul(t, A[i*n+j], N[j]); mpz_add(acc, acc, t); }
        if (mpz_sgn(acc) != 0) { fprintf(stderr, "A*N 第 %ld 行非零\n", i); return 1; }
        mpz_clear(acc); mpz_clear(t);
    }
    printf("iml: nullspace 维数=%ld 且 A*N==0 通过\n", dim);
    return 0;
}
