/* 真实断言：GF(101) 上做矩阵乘法与秩计算，结果可手算。
 * fflas-ffpack 是 header-only，但它依赖 givaro 与 BLAS —— 这个测试同时验证那两条链。 */
#include <cstdio>
#include <givaro/modular.h>
#include <fflas-ffpack/fflas-ffpack.h>

int main() {
    typedef Givaro::Modular<double> Field;
    Field F(101);
    /* A = [[1,2],[3,4]]  B = 单位阵  → A*B 必须等于 A */
    double A[4] = {1, 2, 3, 4};
    double B[4] = {1, 0, 0, 1};
    double C[4] = {0, 0, 0, 0};
    FFLAS::fgemm(F, FFLAS::FflasNoTrans, FFLAS::FflasNoTrans,
                 2, 2, 2, F.one, A, 2, B, 2, F.zero, C, 2);
    for (int i = 0; i < 4; i++)
        if (C[i] != A[i]) { std::fprintf(stderr, "A*I != A 于 [%d]：%g vs %g\n", i, C[i], A[i]); return 1; }

    /* [[1,2],[3,4]] 在 GF(101) 上可逆（det = -2 ≠ 0），秩必须是 2 */
    double D[4] = {1, 2, 3, 4};
    size_t r = FFPACK::Rank(F, 2, 2, D, 2);
    if (r != 2) { std::fprintf(stderr, "rank 应为 2，实得 %zu\n", r); return 1; }
    std::printf("fflas-ffpack: GF(101) 上 A*I==A 通过；rank=2 通过\n");
    return 0;
}
