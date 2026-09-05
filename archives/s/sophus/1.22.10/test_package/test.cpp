#include <cstdio>
#include <sophus/so3.hpp>
#include <sophus/se3.hpp>

int main() {
    // 实质调用 Sophus API: SO(3) 指数映射与 SE(3) 构造
    Eigen::Vector3d omega(0.1, 0.2, 0.3);
    Sophus::SO3d R = Sophus::SO3d::exp(omega);
    Eigen::Matrix3d Rm = R.matrix();
    Eigen::Vector3d t(1.0, 2.0, 3.0);
    Sophus::SE3d T(R, t);
    Eigen::Matrix4d Tm = T.matrix();
    if (!Tm.topLeftCorner<3, 3>().isApprox(Rm, 1e-9)) {
        std::fprintf(stderr, "SE3 rotation mismatch\n");
        return 1;
    }
    if (!Tm.topRightCorner<3, 1>().isApprox(t, 1e-9)) {
        std::fprintf(stderr, "SE3 translation mismatch\n");
        return 1;
    }
    // 逆映射回归: exp(log(R)) == R (log 为实例方法)
    Sophus::SO3d R2 = Sophus::SO3d::exp(R.log());
    if (!R2.matrix().isApprox(Rm, 1e-9)) {
        std::fprintf(stderr, "SO3 exp/log roundtrip mismatch\n");
        return 1;
    }
    std::printf("test sophus 1.22.10: SO3/SE3 exp-log roundtrip OK\n");
    return 0;
}
