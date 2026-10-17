#include <coin/CoinPackedMatrix.hpp>
#include <OsiRowCut.hpp>

#include <cstdio>

int main()
{
    CoinPackedMatrix matrix(false, 0, 0);
    matrix.setDimensions(0, 2);
    if (matrix.getNumCols() != 2 || matrix.getNumElements() != 0) {
        std::fprintf(stderr, "FAIL: CoinPackedMatrix smoke check failed\n");
        return 2;
    }

    OsiRowCut cut;
    cut.setLb(-1.0);
    cut.setUb(1.0);
    if (cut.lb() != -1.0 || cut.ub() != 1.0) {
        std::fprintf(stderr, "FAIL: OsiRowCut bounds check failed\n");
        return 3;
    }

    std::printf("OK: coin-osi 0.108.12 smoke passed\n");
    return 0;
}
