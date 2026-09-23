#include <cstdio>
#include <cstdlib>
#include <cassert>
#include "coin/CoinPackedVector.hpp"

int main(void) {
    // Create a CoinPackedVector and insert elements
    CoinPackedVector vec;
    vec.insert(0, 1.5);
    vec.insert(3, 2.0);
    vec.insert(5, 3.5);

    // Verify element count
    int n = vec.getNumElements();
    assert(n == 3);
    std::printf("CoinPackedVector: %d elements inserted\n", n);

    // Verify element indices and values
    const int* indices = vec.getIndices();
    const double* elements = vec.getElements();
    assert(indices[0] == 0);
    assert(indices[1] == 3);
    assert(indices[2] == 5);
    assert(elements[0] == 1.5);
    assert(elements[1] == 2.0);
    assert(elements[2] == 3.5);
    std::printf("CoinPackedVector: indices and values verified\n");

    // Test max index
    int maxIdx = vec.getMaxIndex();
    assert(maxIdx == 5);
    std::printf("CoinPackedVector: max index = %d\n", maxIdx);

    std::printf("CoinUtils test_package: ALL TESTS PASSED\n");
    return 0;
}