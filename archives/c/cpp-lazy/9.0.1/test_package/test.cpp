#include <Lz/algorithm/accumulate.hpp>
#include <Lz/algorithm/contains.hpp>
#include <Lz/filter.hpp>
#include <Lz/map.hpp>
#include <Lz/procs/to.hpp>
#include <Lz/range.hpp>
#include <Lz/stream.hpp>
#include <Lz/zip.hpp>

#include <iostream>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

namespace {
int checks = 0;
int failures = 0;

void check(bool condition, const char* label) {
    ++checks;
    if (!condition) {
        ++failures;
        std::cerr << "FAIL: " << label << '\n';
    }
}
}  // namespace

int main() {
    const std::vector<int> values{1, 2, 3, 4, 5, 6};
    const auto transformed = values
        | lz::filter([](int value) { return value % 2 == 0; })
        | lz::map([](int value) { return value * 10; })
        | lz::to<std::vector>();

    check(transformed.size() == 3, "pipeline result size");
    check(transformed[0] == 20, "pipeline first value");
    check(transformed[1] == 40, "pipeline second value");
    check(transformed[2] == 60, "pipeline third value");

    const auto numbers = lz::range(1, 6);
    check(lz::accumulate(numbers, 0) == 15, "range accumulate");
    check(lz::contains(numbers, 4), "range contains existing value");
    check(!lz::contains(numbers, 9), "range excludes missing value");

    const std::vector<std::string> names{"one", "two", "three"};
    std::size_t zipped_count = 0;
    int zipped_sum = 0;
    std::string zipped_names;
    for (const auto& item : lz::zip(transformed, names)) {
        ++zipped_count;
        zipped_sum += std::get<0>(item);
        zipped_names += std::get<1>(item);
    }
    check(zipped_count == 3, "zip count");
    check(zipped_sum == 120, "zip numeric aggregation");
    check(zipped_names == "onetwothree", "zip string aggregation");

    std::ostringstream formatted;
    lz::format(transformed, formatted, ", ");
    check(formatted.str() == "20, 40, 60", "fmt-backed formatting");
    check(lz::distance(transformed) == 3, "lazy-view distance");

    if (failures != 0) {
        std::cerr << "RESULT: " << checks << " CHECK, "
                  << (checks - failures) << " PASS, " << failures << " FAIL\n";
        return 1;
    }
    std::cout << "RESULT: 12 CHECK, 12 PASS, 0 FAIL\n";
    return 0;
}
