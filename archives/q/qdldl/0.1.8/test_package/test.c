/*
 * test_package for qdldl 0.1.8
 *
 * 真实调用 QDLDL API：对 2x2 对称矩阵 A = [[2, 0.5], [0.5, 3]]
 * 执行 LDL^T 分解 (QDLDL_etree + QDLDL_factor) 与求解 (QDLDL_solve)，
 * 并与解析结果比对。消费者视角验证头文件可包含、库可链接、API 可用。
 */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <qdldl/qdldl.h>

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond)                                                     \
    do {                                                                \
        g_checks++;                                                     \
        if (!(cond)) {                                                  \
            g_failures++;                                               \
            printf("FAIL line %d: %s\n", __LINE__, #cond);              \
        }                                                               \
    } while (0)

int main(void) {
    const QDLDL_int n = 2;
    /* A = [[2, 0.5], [0.5, 3]] 的上三角部分（CSC 格式） */
    const QDLDL_int Ap[3] = {0, 1, 3};
    const QDLDL_int Ai[3] = {0, 0, 1};
    const QDLDL_float Ax[3] = {2.0, 0.5, 3.0};

    QDLDL_int *etree = (QDLDL_int *)calloc((size_t)n, sizeof(QDLDL_int));
    QDLDL_int *Lnz = (QDLDL_int *)calloc((size_t)n, sizeof(QDLDL_int));
    QDLDL_int *iwork = (QDLDL_int *)calloc((size_t)(3 * n), sizeof(QDLDL_int));
    QDLDL_bool *bwork = (QDLDL_bool *)calloc((size_t)n, sizeof(QDLDL_bool));
    QDLDL_float *fwork = (QDLDL_float *)calloc((size_t)n, sizeof(QDLDL_float));
    if (!etree || !Lnz || !iwork || !bwork || !fwork) {
        printf("FAIL: allocation failed\n");
        return 1;
    }

    QDLDL_int sumLnz = QDLDL_etree(n, Ap, Ai, iwork, Lnz, etree);
    CHECK(sumLnz == 1); /* L 的下三角只有一个非零元 l21 */

    QDLDL_int Lp[3];
    QDLDL_int Li[1];
    QDLDL_float Lx[1];
    QDLDL_float D[2];
    QDLDL_float Dinv[2];

    QDLDL_int st =
        QDLDL_factor(n, Ap, Ai, Ax, Lp, Li, Lx, D, Dinv, Lnz, etree, bwork, iwork, fwork);
    /* 返回 D 中正值个数（>=0 成功；本 SPD 矩阵两个对角元均正，应返回 n=2） */
    CHECK(st == 2);
    CHECK(fabs(D[0] - 2.0) < 1e-12);
    /* D[1] = A22 - A12^2 / A11 = 3 - 0.25/2 = 2.875 */
    CHECK(fabs(D[1] - 2.875) < 1e-12);
    CHECK(fabs(Dinv[0] * D[0] - 1.0) < 1e-12);

    /* 解 A x = b, b = [1,1]^T; 解析解 x = [2.5/5.75, 1.5/5.75]^T (det=5.75) */
    QDLDL_float x[2] = {1.0, 1.0};
    QDLDL_solve(n, Lp, Li, Lx, Dinv, x);
    CHECK(fabs(x[0] - 2.5 / 5.75) < 1e-9);
    CHECK(fabs(x[1] - 1.5 / 5.75) < 1e-9);

    free(etree);
    free(Lnz);
    free(iwork);
    free(bwork);
    free(fwork);

    if (g_failures) {
        printf("qdldl test FAILED: %d/%d checks failed\n", g_failures, g_checks);
        return 1;
    }
    printf("qdldl test PASSED: %d checks passed\n", g_checks);
    return 0;
}
