/* 真实断言：GF(2) 上构造 单位阵与乘法，结果可手算。 */
#include <stdio.h>
#include <stdlib.h>
#include <m4ri/m4ri.h>

int main(void) {
    mzd_t *A = mzd_init(3, 3);
    if (!A) { fprintf(stderr, "mzd_init 失败\n"); return 1; }
    /* A = 单位阵 */
    for (rci_t i = 0; i < 3; i++) mzd_write_bit(A, i, i, 1);
    /* B = 全 1 的第 0 行 */
    mzd_t *B = mzd_init(3, 3);
    for (rci_t j = 0; j < 3; j++) mzd_write_bit(B, 0, j, 1);
    /* I * B == B（单位阵性质，可手算） */
    mzd_t *C = mzd_mul(NULL, A, B, 0);
    if (!C) { fprintf(stderr, "mzd_mul 返回 NULL\n"); return 1; }
    for (rci_t i = 0; i < 3; i++)
        for (rci_t j = 0; j < 3; j++)
            if (mzd_read_bit(C, i, j) != mzd_read_bit(B, i, j)) {
                fprintf(stderr, "I*B != B 于 (%d,%d)\n", i, j); return 1;
            }
    /* 秩：单位阵的秩必须是 3 */
    mzd_t *D = mzd_copy(NULL, A);
    rci_t r = mzd_echelonize(D, 1);
    if (r != 3) { fprintf(stderr, "单位阵的秩应为 3，实得 %d\n", (int)r); return 1; }
    printf("m4ri: I*B==B 通过；rank(I3)=%d 通过\n", (int)r);
    mzd_free(A); mzd_free(B); mzd_free(C); mzd_free(D);
    return 0;
}
