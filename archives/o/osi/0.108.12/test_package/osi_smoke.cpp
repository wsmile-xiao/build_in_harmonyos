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
    std::printf("PASS: CoinPackedMatrix dimensions verified\n");

    OsiRowCut cut;
    cut.setLb(-1.0);
    cut.setUb(1.0);
    if (cut.lb() != -1.0 || cut.ub() != 1.0) {
        std::fprintf(stderr, "FAIL: OsiRowCut bounds check failed\n");
        return 3;
    }
    std::printf("PASS: OsiRowCut bounds verified\n");

    std::printf("OK: osi 0.108.12 smoke passed\n");
    std::printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"./osi_smoke\",\"discovered\":2,\"passedCount\":2}\n");
    return 0;
}
