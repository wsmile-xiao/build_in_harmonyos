// test_tbb.cpp — L1 smoke test for oneTBB shared library
// Verifies tbb::parallel_for is linkable and produces correct results.
#include <tbb/parallel_for.h>
#include <tbb/blocked_range.h>
#include <vector>
#include <iostream>
#include <cassert>

int main() {
    const int N = 1000;
    std::vector<int> data(N, 0);

    tbb::parallel_for(tbb::blocked_range<int>(0, N),
        [&](const tbb::blocked_range<int>& r) {
            for (int i = r.begin(); i < r.end(); ++i) {
                data[i] = i * 2;
            }
        });

    // Verify results
    for (int i = 0; i < N; ++i) {
        assert(data[i] == i * 2);
    }

    std::cout << "PASS: tbb::parallel_for computed " << N
              << " elements correctly" << std::endl;
    return 0;
}
