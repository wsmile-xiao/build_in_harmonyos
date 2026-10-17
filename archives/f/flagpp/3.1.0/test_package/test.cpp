// test_package consumer test for flagpp 3.1.0 (R34: must actually use the API)
// flagpp's operators are global templates constrained by flagpp::enabled<Enum>,
// found via unqualified lookup on scoped-enum operands.
#include <cassert>
#include <flagpp/flags.hpp>
#include <iostream>

enum class color : unsigned
{
    none   = 0,
    red    = 1 << 0,
    green  = 1 << 1,
    blue   = 1 << 2,
};

template <>
constexpr bool flagpp::enabled<color> = true;

int main()
{
    color c = color::red | color::green;
    // red|green must include red and green, and exclude blue
    assert((c & color::red) == color::red);
    assert((c & color::green) == color::green);
    assert((c & color::blue) == color::none);

    // xor toggles green away
    color d = c ^ color::green;
    assert((d & color::green) == color::none);
    assert((d & color::red) == color::red);

    // combined check of all three bits
    color all = color::red | color::green | color::blue;
    assert((all & color::red) == color::red);
    assert((all & color::green) == color::green);
    assert((all & color::blue) == color::blue);

    std::cout << "flagpp 3.1.0 consumer test: OK (bitwise ops on scoped enum)"
              << std::endl;
    return 0;
}
