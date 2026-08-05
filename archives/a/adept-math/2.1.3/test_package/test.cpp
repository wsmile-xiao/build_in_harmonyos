#include <adept.h>

#include <cmath>
#include <iostream>

int main()
{
    adept::Stack stack;
    adept::adouble x = 3.0;

    stack.new_recording();
    adept::adouble y = x * x + 2.0 * x;
    y.set_gradient(1.0);
    stack.reverse();

    const double grad = x.get_gradient();
    if (std::fabs(grad - 8.0) > 1.0e-12) {
        std::cerr << "unexpected derivative: " << grad << "\n";
        return 1;
    }

    if (adept::have_matrix_multiplication() || adept::have_linear_algebra()) {
        std::cerr << "optional BLAS/LAPACK features should be disabled\n";
        return 1;
    }

    return 0;
}
