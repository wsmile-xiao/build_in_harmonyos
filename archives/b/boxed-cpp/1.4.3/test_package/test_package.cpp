// SPDX-License-Identifier: Apache-2.0
// Consumer test: include the installed header and exercise the public API.
#include <boxed-cpp/boxed.hpp>

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <type_traits>

namespace tags
{
struct Length
{
};
struct From
{
};
struct To
{
};
} // namespace tags

using Length = boxed::boxed<std::size_t, tags::Length>;
using From = boxed::boxed<std::size_t, tags::From>;
using To = boxed::boxed<std::size_t, tags::To>;
using BoxedDouble = boxed::boxed<double>;

int main()
{
    // construction + == / != / < comparison
    Length constexpr l1 { 1 };
    Length constexpr l2 { 2 };
    static_assert(l1 == l1);
    static_assert(l1 != l2);
    static_assert(l1 < l2);

    // unbox() returns the underlying value; runtime value check
    BoxedDouble bd { 3.14 };
    static_assert(std::is_same_v<decltype(unbox(bd)), double>);
    if (std::abs(unbox(bd) - 3.14) > 1e-12)
        return EXIT_FAILURE;

    // .as<T>() conversion to another boxed type / native type
    From constexpr f { 3 };
    To constexpr t = f.as<To>();
    static_assert(t == To { 3 });
    auto constexpr tint = f.as<int>();
    if (tint != 3)
        return EXIT_FAILURE;

    // boxed_cast
    auto constexpr tc = boxed_cast<To>(f);
    static_assert(*tc == *f);
    static_assert(std::is_same_v<decltype(tc), To const>);

    // arithmetic on boxed doubles stays boxed
    BoxedDouble speed { 299792458.0 };
    auto dist = speed * 2.0;
    static_assert(std::is_same_v<decltype(dist), BoxedDouble>);
    if (std::abs(unbox(dist) - 599584916.0) > 1e-6)
        return EXIT_FAILURE;

    std::cout << "boxed-cpp consumer test passed\n";
    return EXIT_SUCCESS;
}
