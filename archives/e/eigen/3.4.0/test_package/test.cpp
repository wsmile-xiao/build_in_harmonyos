#include <iostream>
#include <Eigen/Dense>

int main() {
    Eigen::Matrix2d m;
    m << 1, 2,
         3, 4;
    Eigen::Vector2d v(5, 6);
    Eigen::Vector2d result = m * v;
    if (result(0) != 17 || result(1) != 39) {
        std::cerr << "Eigen test FAILED: expected (17, 39), got ("
                  << result(0) << ", " << result(1) << ")" << std::endl;
        return 1;
    }
    std::cout << "Eigen test PASSED: matrix-vector multiplication works" << std::endl;
    return 0;
}
