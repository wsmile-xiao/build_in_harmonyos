#include <fixed_string.hpp>
#include <cassert>

int main() {
    // basic_fixed_string construction & comparison (C++17)
    constexpr fixstr::fixed_string foo = "foo";
    constexpr fixstr::fixed_string bar = "bar";
    static_assert(foo == foo, "equality");
    static_assert(foo != bar, "inequality");
    static_assert(foo.size() == 3, "size");
    // Concatenation at compile time
    constexpr auto foobar = foo + bar;
    static_assert(foobar.size() == 6, "concat size");
    return 0;
}
