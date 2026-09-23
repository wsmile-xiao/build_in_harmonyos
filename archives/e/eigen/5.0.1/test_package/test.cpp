#include <Eigen/Dense>

#include <cstdio>


int main() {
    Eigen::Matrix2d matrix;
    matrix << 1, 2,
              3, 4;
    const Eigen::Matrix2d squared = matrix * matrix;

    if (squared(0, 0) != 7 || squared(0, 1) != 10 ||
        squared(1, 0) != 15 || squared(1, 1) != 22) {
        std::fprintf(stderr, "FAIL: matrix multiply mismatch\n");
        return 1;
    }

    const Eigen::Vector3d vector(3.0, 4.0, 0.0);
    if (vector.norm() != 5.0) {
        std::fprintf(stderr, "FAIL: vector norm mismatch (got %f)\n", vector.norm());
        return 1;
    }

    std::printf("eigen smoke test: PASS (matmul + norm OK)\n");
    return 0;
}
