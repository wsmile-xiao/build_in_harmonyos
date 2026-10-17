#include <iostream>
#include <vector>

#include <oneapi/tbb/blocked_range.h>
#include <oneapi/tbb/parallel_for.h>

int main() {
    constexpr int count = 1000;
    std::vector<int> values(count, 0);
    oneapi::tbb::parallel_for(oneapi::tbb::blocked_range<int>(0, count),
        [&values](const oneapi::tbb::blocked_range<int>& range) {
            for (int i = range.begin(); i != range.end(); ++i) {
                values[i] = i * 2;
            }
        });
    for (int i = 0; i != count; ++i) {
        if (values[i] != i * 2) {
            std::cerr << "FAIL: oneTBB parallel_for mismatch at " << i << "\n";
            return 1;
        }
    }
    std::cout << "PASS: oneTBB parallel_for computed " << count << " elements\n";
    return 0;
}
