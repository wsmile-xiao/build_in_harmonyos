#include <stdint.h>
#include <stddef.h>
#include <urdf_model/model.h>
#include <urdf_model/pose.h>

#include <cmath>
#include <cstdio>

// urdfdom_headers 3.0.0 —— 纯头库，真实数学验证（非空壳）。
// 头库没有 .so 可链，所以「能不能用」全靠**头闭包完整 + 内联实现算得对**：
//   ① Rotation::setFromRPY / getRPY 往返保真
//   ② 四元数绕 Z 转 90°：(1,0,0) → (0,1,0)（闭式解对账）
//   ③ Rotation 复合：两次 90° = 一次 180°
//   ④ Pose 与 Link/Joint 类型可实例化（证明 model.h 的头闭包没缺件）

static int failures = 0;

#define CHECK(cond, msg)                                                     \
  do {                                                                       \
    if (!(cond)) {                                                           \
      std::fprintf(stderr, "[FAIL] %s  (%s:%d)\n", msg, __FILE__, __LINE__); \
      ++failures;                                                            \
    } else {                                                                 \
      std::printf("[ok] %s\n", msg);                                         \
    }                                                                        \
  } while (0)

static bool near(double a, double b, double eps = 1e-9) {
  return std::fabs(a - b) < eps;
}

int main() {
  const double PI = 3.14159265358979323846;

  // ① RPY 往返
  {
    urdf::Rotation r;
    r.setFromRPY(0.1, -0.2, 0.3);
    double roll = 0, pitch = 0, yaw = 0;
    r.getRPY(roll, pitch, yaw);
    CHECK(near(roll, 0.1, 1e-9) && near(pitch, -0.2, 1e-9) && near(yaw, 0.3, 1e-9),
          "setFromRPY/getRPY 往返保真");
    if (!near(roll, 0.1, 1e-9))
      std::fprintf(stderr, "       实得 rpy=(%.12f, %.12f, %.12f)\n", roll, pitch, yaw);
  }

  // ② 绕 Z 转 90°
  {
    urdf::Rotation rz;
    rz.setFromRPY(0, 0, PI / 2);
    urdf::Vector3 v(1, 0, 0);
    urdf::Vector3 out = rz * v;
    CHECK(near(out.x, 0.0, 1e-9) && near(out.y, 1.0, 1e-9) && near(out.z, 0.0, 1e-9),
          "绕 Z 转 90°：(1,0,0)→(0,1,0)");
    if (!near(out.y, 1.0, 1e-9))
      std::fprintf(stderr, "       实得 (%.12f, %.12f, %.12f)\n", out.x, out.y, out.z);
  }

  // ③ 复合：两次 90° == 一次 180°
  {
    urdf::Rotation a;
    a.setFromRPY(0, 0, PI / 2);
    urdf::Rotation twice = a * a;
    urdf::Vector3 out = twice * urdf::Vector3(1, 0, 0);
    CHECK(near(out.x, -1.0, 1e-9) && near(out.y, 0.0, 1e-9),
          "两次绕 Z 90° 复合 = 180°：(1,0,0)→(-1,0,0)");
  }

  // ④ 头闭包：model.h 引到的类型都能实例化
  {
    urdf::Pose p;
    p.position = urdf::Vector3(1, 2, 3);
    p.rotation.setFromRPY(0, 0, 0);
    CHECK(near(p.position.z, 3.0), "Pose 可构造并读回 position");

    urdf::Link link;
    link.name = "base_link";
    urdf::Joint joint;
    joint.name = "j1";
    joint.type = urdf::Joint::REVOLUTE;
    urdf::ModelInterface model;
    model.name_ = "probe";
    CHECK(link.name == "base_link" && joint.type == urdf::Joint::REVOLUTE
              && model.name_ == "probe",
          "Link / Joint / ModelInterface 头闭包完整可用");
  }

  if (failures) {
    std::fprintf(stderr, "\nurdfdom_headers: %d 项断言失败\n", failures);
    return 1;
  }
  std::printf("\nurdfdom_headers 3.0.0: 全部断言通过\n");
  return 0;
}
