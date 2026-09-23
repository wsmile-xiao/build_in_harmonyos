#include "Fastor/Fastor.h"
#include <cmath>
#include <cstdio>

using namespace Fastor;

int main() {
    // Real consumer test: build a tensor, fill it, run a matmul and a
    // reduction, and verify the results numerically (R34: must actually
    // consume the library API, not just print).
    Tensor<double, 2, 2> A;
    A(0, 0) = 1.0; A(0, 1) = 2.0;
    A(1, 0) = 3.0; A(1, 1) = 4.0;

    Tensor<double, 2, 2> B;
    B(0, 0) = 5.0; B(0, 1) = 6.0;
    B(1, 0) = 7.0; B(1, 1) = 8.0;

    auto C = matmul(A, B);
    // C = [[19, 22], [43, 50]]
    if (std::abs(C(0, 0) - 19.0) > 1e-9 || std::abs(C(0, 1) - 22.0) > 1e-9 ||
        std::abs(C(1, 0) - 43.0) > 1e-9 || std::abs(C(1, 1) - 50.0) > 1e-9) {
        std::printf("fastor 0.6.4 matmul FAILED: C00=%f C01=%f C10=%f C11=%f\n",
                    C(0, 0), C(0, 1), C(1, 0), C(1, 1));
        return 1;
    }

    // Reduction over a 3-element vector: sum([1,2,3]) == 6
    Tensor<double, 3> v;
    v(0) = 1.0; v(1) = 2.0; v(2) = 3.0;
    double s = sum(v);
    if (std::abs(s - 6.0) > 1e-9) {
        std::printf("fastor 0.6.4 sum FAILED: %f\n", s);
        return 1;
    }

    std::printf("fastor 0.6.4 consumer test OK (matmul + sum verified)\n");
    return 0;
}
