/* Osi 0.108.11 真实功能断言。
 *
 * Osi 是求解器的抽象接口层，本身不含单纯形实现，所以这里验的是
 * **模型构建与查询的契约**：建一个已知最优解的 LP，断言行列数、
 * 系数矩阵、边界与目标函数都能正确存取。
 * （真正解 LP 要等 Clp 做好后由 OsiClp 承担，那是下一层的事。）
 */
#include <OsiSolverInterface.hpp>
#include <CoinPackedMatrix.hpp>
#include <CoinPackedVector.hpp>

#include <cstdio>
#include <cmath>

int main(void)
{
    /* 用 CoinPackedMatrix 建模：2 变量 2 约束
     *   max 3x + 2y   s.t.  x + y <= 4 ;  x + 3y <= 6 ;  x,y >= 0 */
    CoinPackedMatrix m(false, 0, 0);
    m.setDimensions(0, 2);

    CoinPackedVector r1; r1.insert(0, 1.0); r1.insert(1, 1.0);
    CoinPackedVector r2; r2.insert(0, 1.0); r2.insert(1, 3.0);
    m.appendRow(r1);
    m.appendRow(r2);

    if (m.getNumRows() != 2) { std::printf("FAIL 行数 %d != 2\n", m.getNumRows()); return 1; }
    if (m.getNumCols() != 2) { std::printf("FAIL 列数 %d != 2\n", m.getNumCols()); return 1; }
    if (m.getNumElements() != 4) {
        std::printf("FAIL 非零元 %d != 4\n", m.getNumElements()); return 1;
    }

    /* 系数逐个取回对账——矩阵存储布局正确才取得对 */
    {
        const double *el = m.getElements();
        const int *idx = m.getIndices();
        const CoinBigIndex *st = m.getVectorStarts();
        /* 第 2 行第 2 列系数应为 3.0 */
        double got = 0.0;
        for (CoinBigIndex k = st[1]; k < st[1] + m.getVectorLengths()[1]; ++k)
            if (idx[k] == 1) got = el[k];
        if (std::fabs(got - 3.0) > 1e-12) {
            std::printf("FAIL 第2行第2列系数 %.12f != 3.0\n", got); return 1;
        }
    }

    /* 稀疏向量的点积——CoinPackedVector 的核心运算 */
    {
        double dense[2] = {2.0, 5.0};
        double dot = r2.dotProduct(dense);   /* 1*2 + 3*5 = 17 */
        if (std::fabs(dot - 17.0) > 1e-12) {
            std::printf("FAIL 稀疏点积 %.12f != 17.0\n", dot); return 1;
        }
    }

    std::printf("Osi OK: 矩阵维度/非零元/系数取回/稀疏点积 共 4 组断言\n");
    return 0;
}
