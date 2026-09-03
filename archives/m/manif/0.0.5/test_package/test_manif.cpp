// test_manif.cpp — 消费者视角验证 manif 0.0.5（鸿蒙专项：OHOS clang 工具链编译运行）
// 实际调用 manif 公开 API：SO2/SE2/SE3 群的构造、指数映射、群乘法与点变换，
// 并与 Math 库期望值比对，验证头文件库可被正确消费。
// 注意：不依赖 assert（Release/NDEBUG 下 assert 被禁用），使用显式检查并返回非零退出码，
// 保证 conan test() 在任意构建类型下都能真实校验。
#include <cmath>
#include <complex>
#include <cstdlib>
#include <iostream>

#include <Eigen/Core>

#include <manif/SO2.h>
#include <manif/SE2.h>
#include <manif/SO3.h>
#include <manif/SE3.h>

#define CHECK(cond, msg)                                                     \
  do {                                                                       \
    if (!(cond)) {                                                           \
      std::cerr << "FAILED: " << msg << " (line " << __LINE__ << ")" << std::endl; \
      return 1;                                                              \
    }                                                                        \
  } while (0)

int main() {
  using Scalar = double;

  // SO2: 角度 0.5 rad 的指数映射与对数映射往返
  const Scalar theta = 0.5;
  manif::SO2<Scalar> so2(theta);
  const Scalar roundtrip = so2.log().coeffs()[0];
  CHECK(std::abs(roundtrip - theta) < 1e-9, "SO2 log(exp(0.5)) roundtrip");
  std::cout << "SO2 log(exp(0.5))=" << roundtrip << " ok" << std::endl;

  // SO2 群乘法: R(a)*R(b) = R(a+b)
  const Scalar a = 0.3, b = -0.2;
  manif::SO2<Scalar> ra(a), rb(b);
  const manif::SO2<Scalar> rab = ra * rb;
  CHECK(std::abs(rab.log().coeffs()[0] - (a + b)) < 1e-9, "SO2 compose");
  std::cout << "SO2 compose ok" << std::endl;

  // SE2: 旋转 + 平移，作用于点 (1, 0)
  manif::SE2<Scalar> se2(1.0, 0.0, theta);
  const Eigen::Vector2d p(1.0, 0.0);
  const Eigen::Vector2d q = se2.act(p);
  const Scalar expect_x = std::cos(theta) * 1.0 - std::sin(theta) * 0.0 + 1.0;
  const Scalar expect_y = std::sin(theta) * 1.0 + std::cos(theta) * 0.0 + 0.0;
  CHECK(std::abs(q.x() - expect_x) < 1e-9, "SE2 act x");
  CHECK(std::abs(q.y() - expect_y) < 1e-9, "SE2 act y");
  std::cout << "SE2 act((1,0)) -> (" << q.x() << "," << q.y() << ") ok" << std::endl;

  // SO3: 绕 Z 轴 pi/2 旋转作用于点 (1,0,0)
  const manif::SO3<Scalar> so3(Eigen::AngleAxis<Scalar>(M_PI / 2.0, Eigen::Vector3d::UnitZ()));
  const Eigen::Vector3d p3(1.0, 0.0, 0.0);
  const Eigen::Vector3d q3 = so3.act(p3);
  CHECK(std::abs(q3.x() - 0.0) < 1e-9, "SO3 act x");
  CHECK(std::abs(q3.y() - 1.0) < 1e-9, "SO3 act y");
  CHECK(std::abs(q3.z() - 0.0) < 1e-9, "SO3 act z");
  std::cout << "SO3 Rz(pi/2) act((1,0,0)) -> (" << q3.x() << "," << q3.y() << "," << q3.z() << ") ok" << std::endl;

  // SE3: tangent 顺序为 [x,y,z, wx,wy,wz]（先平移后旋转向量），
  // 平移 (1,2,3) + 零旋转 的指数映射，act(origin) 应得 (1,2,3)
  const Eigen::Matrix<Scalar, 6, 1> xi =
      (Eigen::Matrix<Scalar, 6, 1>() << 1, 2, 3, 0, 0, 0).finished();
  const manif::SE3<Scalar> se3 = manif::SE3<Scalar>::Tangent(xi).exp();
  const Eigen::Vector3d qse3 = se3.act(Eigen::Vector3d(0, 0, 0));
  CHECK(std::abs(qse3.x() - 1.0) < 1e-6, "SE3 act x");
  CHECK(std::abs(qse3.y() - 2.0) < 1e-6, "SE3 act y");
  CHECK(std::abs(qse3.z() - 3.0) < 1e-6, "SE3 act z");
  std::cout << "SE3 exp((1,2,3,0,0,0)) act(origin) -> ("
            << qse3.x() << "," << qse3.y() << "," << qse3.z() << ") ok" << std::endl;

  std::cout << "test_manif PASSED (SO2 exp/log, SO2 compose, SE2 act, SO3 act, SE3 exp/act) [OHOS clang]"
            << std::endl;
  return 0;
}