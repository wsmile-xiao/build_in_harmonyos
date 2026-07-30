#include <blaze/Math.h>

#include <cmath>
#include <iostream>

int main() {
    blaze::DynamicMatrix<double> a{{1.0, 2.0}, {3.0, 4.0}};
    blaze::DynamicMatrix<double> b{{2.0, 0.0}, {1.0, 2.0}};
    const auto product = a * b;

    if (std::fabs(product(0, 0) - 4.0) > 1e-12 ||
        std::fabs(product(1, 1) - 8.0) > 1e-12) {
        return 1;
    }

    std::cout << "blaze test_package passed\n";
    return 0;
}
