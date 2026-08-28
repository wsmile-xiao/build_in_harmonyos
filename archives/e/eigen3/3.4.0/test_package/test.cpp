#include <iostream>
#include <Eigen/Dense>

int main() {
    Eigen::MatrixXd m(2, 2);
    m(0, 0) = 3;
    m(1, 0) = 2.5;
    m(0, 1) = -1;
    m(1, 1) = m(1, 0) + m(0, 0);
    Eigen::MatrixXd r = m * m;
    if (r.rows() == 2 && r.cols() == 2) {
        std::cout << "eigen3 3.4.0 OK" << std::endl;
        return 0;
    }
    return 1;
}
