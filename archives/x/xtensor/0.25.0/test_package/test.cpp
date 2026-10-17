#include <cmath>
#include <iostream>

#include <xtensor/xarray.hpp>
#include <xtensor/xmath.hpp>

int main()
{
    xt::xarray<double> input = {{1.0, 2.0}, {3.0, 4.0}};
    auto shifted = input + 2.0;

    if (std::fabs(shifted(1, 1) - 6.0) > 1e-12)
    {
        std::cerr << "xtensor expression evaluation failed\n";
        return 1;
    }

    const double total = xt::sum(shifted)();
    if (std::fabs(total - 18.0) > 1e-12)
    {
        std::cerr << "xtensor reduction failed: " << total << "\n";
        return 2;
    }

    return 0;
}
