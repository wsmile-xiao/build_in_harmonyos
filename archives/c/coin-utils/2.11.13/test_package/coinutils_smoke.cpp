#include <CoinPackedMatrix.hpp>

#include <cstdio>
#include <exception>

int main()
{
    try {
        CoinPackedMatrix matrix;
        const int elements = matrix.getNumElements();
        std::printf("CoinPackedMatrix::getNumElements() = %d\n", elements);
        if (elements != 0) {
            std::fprintf(stderr, "FAIL: expected a default matrix to be empty\n");
            return 2;
        }
        std::puts("OK: coin-utils 2.11.13 smoke test passed.");
        return 0;
    } catch (const std::exception &error) {
        std::fprintf(stderr, "std::exception: %s\n", error.what());
        return 3;
    }
}
