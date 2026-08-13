/* 真实断言：整数矩阵的行列式与秩，结果可手算。
 * linbox 把 givaro/fflas-ffpack/ntl/flint/iml 串在一起 —— 这个测试等于验整条链。 */
#include <cstdio>
#include <iostream>
#include <linbox/linbox-config.h>
#include <linbox/ring/modular.h>
#include <linbox/matrix/dense-matrix.h>
#include <linbox/solutions/det.h>
#include <linbox/solutions/rank.h>

int main() {
    typedef Givaro::ZRing<Givaro::Integer> Ints;
    Ints Z;
    /* A = [[1,2],[3,4]]  →  det = 1*4-2*3 = -2，秩 = 2（可手算） */
    LinBox::DenseMatrix<Ints> A(Z, 2, 2);
    A.setEntry(0, 0, Givaro::Integer(1)); A.setEntry(0, 1, Givaro::Integer(2));
    A.setEntry(1, 0, Givaro::Integer(3)); A.setEntry(1, 1, Givaro::Integer(4));

    Givaro::Integer d;
    LinBox::det(d, A);
    if (d != Givaro::Integer(-2)) {
        /* Givaro::Integer 没有 get_str()，只重载了 operator<<，故走 iostream */
        std::cerr << "det([[1,2],[3,4]]) 应为 -2，实得 " << d << "\n";
        return 1;
    }
    unsigned long r;
    LinBox::rank(r, A);
    if (r != 2) { std::fprintf(stderr, "rank 应为 2，实得 %lu\n", r); return 1; }

    /* B = [[1,2],[2,4]] 秩亏 → det = 0，秩 = 1 */
    LinBox::DenseMatrix<Ints> B(Z, 2, 2);
    B.setEntry(0, 0, Givaro::Integer(1)); B.setEntry(0, 1, Givaro::Integer(2));
    B.setEntry(1, 0, Givaro::Integer(2)); B.setEntry(1, 1, Givaro::Integer(4));
    Givaro::Integer d2; LinBox::det(d2, B);
    if (d2 != Givaro::Integer(0)) { std::fprintf(stderr, "秩亏阵的 det 应为 0\n"); return 1; }
    unsigned long r2; LinBox::rank(r2, B);
    if (r2 != 1) { std::fprintf(stderr, "秩亏阵的 rank 应为 1，实得 %lu\n", r2); return 1; }

    std::printf("linbox: det=-2/rank=2 通过；秩亏阵 det=0/rank=1 通过\n");
    return 0;
}
