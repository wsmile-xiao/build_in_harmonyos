#include <cmath>
#include <iostream>

#include <alglib/interpolation.h>
#include <alglib/linalg.h>

int main()
{
    alglib::real_2d_array matrix("[[4,1],[1,3]]");
    if (!alglib::spdmatrixcholesky(matrix, 2, true)) {
        std::cerr << "spdmatrixcholesky failed\n";
        return 1;
    }

    alglib::real_1d_array x("[0,1,2]");
    alglib::real_1d_array y("[0,1,4]");
    alglib::spline1dinterpolant spline;
    alglib::spline1dbuildlinear(x, y, spline);
    const double value = alglib::spline1dcalc(spline, 0.5);
    if (std::fabs(value - 0.5) > 1e-12) {
        std::cerr << "unexpected spline value: " << value << "\n";
        return 1;
    }

    std::cout << "alglib consumer API validation OK\n";
    return 0;
}
