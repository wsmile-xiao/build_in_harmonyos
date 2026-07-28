#include <cmath>
#include <iostream>

#include <xsimd/xsimd.hpp>

int main()
{
    using batch = xsimd::batch<double>;

    double lhs[batch::size];
    double rhs[batch::size];
    double out[batch::size];

    for (std::size_t i = 0; i < batch::size; ++i)
    {
        lhs[i] = static_cast<double>(i);
        rhs[i] = 2.0;
        out[i] = 0.0;
    }

    auto result = batch::load_unaligned(lhs) + batch::load_unaligned(rhs);
    result.store_unaligned(out);

    for (std::size_t i = 0; i < batch::size; ++i)
    {
        const double expected = static_cast<double>(i) + 2.0;
        if (std::fabs(out[i] - expected) > 1e-12)
        {
            std::cerr << "xsimd batch addition failed at " << i << "\n";
            return 1;
        }
    }

    return 0;
}
