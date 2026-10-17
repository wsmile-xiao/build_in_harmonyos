#include <brigand/brigand.hpp>
#include <brigand/algorithms.hpp>
#include <brigand/sequences/list.hpp>
#include <cstdio>
#include <type_traits>

// Real consumer test: exercise brigand meta-programming on OHOS arm64.
// Compile-time assertions fail the build if any meta-function regresses.
using ints = brigand::integral_list<int, 1, 2, 3, 4>;
static_assert(brigand::size<ints>::value == 4, "size");
static_assert(std::is_same<brigand::front<ints>, std::integral_constant<int, 1>>::value,
              "front");
static_assert(std::is_same<brigand::at<ints, std::integral_constant<int, 2>>,
              std::integral_constant<int, 3>>::value, "at");

// count_if: number of elements whose predicate is true (bind + placeholder)
template <typename N>
using is_odd = brigand::bool_<(N::value % 2) != 0>;
static_assert(brigand::count_if<ints, brigand::bind<is_odd, brigand::_1>>::value == 2,
              "count_if");

using nums = brigand::list<std::integral_constant<int, 1>, std::integral_constant<int, 7>,
                           std::integral_constant<int, 2>, std::integral_constant<int, 9>>;
static_assert(brigand::all<std::integral_constant<int, 1>>::value, "all");
static_assert(brigand::any<brigand::integral_list<int, 0, 0, 7, 0>>::value, "any");

int main() {
    std::printf("brigand 1.3.0 consumer test OK (size=%d)\n",
                static_cast<int>(brigand::size<ints>::value));
    return 0;
}