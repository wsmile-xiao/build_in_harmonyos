// test_package/test.cpp — eigen 消费者测试
// 验证可包含 Eigen/Dense 并做矩阵运算。
#include <Eigen/Dense>
#include <cstdio>

int main() {
    Eigen::Matrix2d m;
    m << 1, 2,
         3, 4;
    Eigen::Matrix2d m2 = m * m;

    // 验证矩阵乘法结果 (1*1+2*3=7, 1*2+2*4=10, 3*1+4*3=15, 3*2+4*4=22)
    if (m2(0, 0) != 7 || m2(0, 1) != 10 || m2(1, 0) != 15 || m2(1, 1) != 22) {
        fprintf(stderr, "FAIL: matrix multiply mismatch\n");
        return 1;
    }

    // 向量范数
    Eigen::Vector3d v(3.0, 4.0, 0.0);
    if (v.norm() != 5.0) {
        fprintf(stderr, "FAIL: vector norm mismatch (got %f)\n", v.norm());
        return 1;
    }

    printf("eigen smoke test: PASS (matmul + norm OK)\n");
    return 0;
}
