#include <iostream>

#include <xtl/xoptional.hpp>
#include <xtl/xvariant.hpp>

int main()
{
    auto present = xtl::optional(42, true);
    auto missing = xtl::optional(7, false);

    if (!present.has_value() || present.value() != 42)
    {
        std::cerr << "xtl optional present value check failed\n";
        return 1;
    }
    if (missing.has_value() || missing.value_or(9) != 9)
    {
        std::cerr << "xtl optional missing value check failed\n";
        return 2;
    }

    xtl::variant<int, double> value = 5;
    if (xtl::xget<int>(value) != 5)
    {
        std::cerr << "xtl variant xget check failed\n";
        return 3;
    }

    return 0;
}
