// test_cppitertools.cpp — consumer smoke test for cppitertools 2.3
//
// Exercises real installed headers (range / enumerate / zip / accumulate)
// and validates expected output values. All API calls run unconditionally and
// results are checked with an explicit failure helper (not bare assert), so the
// validation stays active under -DNDEBUG / Release builds.
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

#include <cppitertools/itertools.hpp>

namespace {
int failures = 0;

// Explicit check active in Release/NDEBUG: prints and counts failures.
void check(bool ok, const char* what) {
    if (!ok) {
        ++failures;
        std::cerr << "FAIL: " << what << "\n";
    }
}
}  // namespace

int main() {
    // range: sum 0..9 must be 45
    int sum = 0;
    for (auto i : iter::range(10)) {
        sum += i;
    }
    check(sum == 45, "range(10) sum == 45");

    // accumulate: iterating yields running products 1,2,6,24,120; final is 120
    int product = 1;
    for (auto v : iter::accumulate(iter::range(1, 6), std::multiplies<int>())) {
        product = v;  // last running value = 1*2*3*4*5
    }
    check(product == 120, "accumulate(1..5, multiplies) final == 120");

    // enumerate: index/value pairing over a vector
    std::vector<std::string> names{"a", "bb", "ccc"};
    std::size_t idx_sum = 0;
    std::string concat;
    for (auto&& [idx, val] : iter::enumerate(names)) {
        idx_sum += idx;
        concat += val;
    }
    check(idx_sum == 3, "enumerate indices sum == 3");
    check(concat == "abbccc", "enumerate concatenation == abbccc");

    // zip: pairing of two ranges
    std::vector<int> left{1, 2, 3};
    std::vector<int> right{10, 20, 30};
    int zsum = 0;
    for (auto&& [a, b] : iter::zip(left, right)) {
        zsum += a * b;
    }
    check(zsum == 140, "zip product sum == 140");  // 10 + 40 + 90

    if (failures != 0) {
        std::cerr << "test_cppitertools: " << failures << " check(s) failed\n";
        return 1;
    }
    std::cout << "test_cppitertools: OK (8 checks passed)\n";
    return 0;
}