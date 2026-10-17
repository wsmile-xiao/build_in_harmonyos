#include <burst/algorithm/radix_sort.hpp>
#include <burst/container/dynamic_tuple.hpp>
#include <burst/integer/intpow.hpp>
#include <burst/range/intersect.hpp>

#include <deque>
#include <iostream>
#include <list>
#include <string>
#include <tuple>
#include <vector>

int main()
{
    // 1. Integer radix sort.
    std::vector<int> values{42, -7, 19, 0, -11, 5};
    std::vector<int> buffer(values.size());
    burst::radix_sort(values.begin(), values.end(), buffer.begin());
    if (values != std::vector<int>{-11, -7, 0, 5, 19, 42}) {
        std::cerr << "radix_sort produced an unexpected order\n";
        return 1;
    }

    // 2. Lazy intersection over three differently-typed sorted ranges.
    std::vector<int> natural{1, 2, 3, 4, 5, 6, 7};
    std::list<int> prime{2, 3, 5, 7};
    std::deque<int> odd{1, 3, 5, 7};
    const auto intersection = burst::intersect(std::tie(natural, prime, odd));
    if (std::vector<int>(intersection.begin(), intersection.end()) !=
        std::vector<int>{3, 5, 7}) {
        std::cerr << "intersect produced an unexpected range\n";
        return 1;
    }

    // 3. Runtime heterogeneous tuple storage and typed access.
    burst::dynamic_tuple tuple(std::string("HarmonyOS"));
    tuple.push_back(311u);
    if (tuple.size() != 2) {
        std::cerr << "dynamic_tuple has an unexpected size\n";
        return 1;
    }
    if (tuple.get<std::string>(0) != "HarmonyOS") {
        std::cerr << "dynamic_tuple string value is incorrect\n";
        return 1;
    }
    if (tuple.get<unsigned>(1) != 311u) {
        std::cerr << "dynamic_tuple unsigned value is incorrect\n";
        return 1;
    }

    // 4. Constexpr integer utility.
    static_assert(burst::intpow(3, 4) == 81, "burst::intpow must be constexpr");

    std::cout << "Burst consumer test passed: 4 scenarios, 6 assertions\n";
    return 0;
}
