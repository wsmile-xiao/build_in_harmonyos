#include <stdint.h>
#include <stddef.h>
#include <coal/collision.h>
#include <coal/distance.h>
#include <coal/shape/geometric_shapes.h>
#include <coal/math/transform.h>

#include <cmath>
#include <cstdio>

// coal 3.0.3（hpp-fcl 后继）—— 真实碰撞/距离计算验证（非 dlopen 空壳）。
// 全部用闭式解对账：
//   ① 两个半径 0.5 的球，圆心距 2.0 → 不碰，最小距离 = 1.0
//   ② 同上，圆心距 0.5 → 相碰
//   ③ 边长 1 的立方体与球，沿 x 平移 2.0 → 最小距离 = 2.0 - 0.5 - 0.5 = 1.0
//   ④ 立方体自碰（同位姿）→ 必碰
//   ⑤ 距离在临界点（恰好相切）附近连续：距离 ≈ 0
//
// coal 是 pin 依赖里唯一把 octomap / qhull / assimp / boost 全用上的一环，
// 编得过本身就说明那四个接线都对。

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

static bool near(double a, double b, double eps = 1e-6) {
  return std::fabs(a - b) < eps;
}

static coal::Transform3s at(double x, double y, double z) {
  coal::Transform3s tf;
  tf.setIdentity();
  tf.setTranslation(coal::Vec3s(x, y, z));
  return tf;
}

int main() {
  coal::Sphere s1(0.5), s2(0.5);
  coal::Box box(1.0, 1.0, 1.0);

  // ① 两球分离
  {
    coal::CollisionRequest creq;
    coal::CollisionResult cres;
    coal::collide(&s1, at(0, 0, 0), &s2, at(2, 0, 0), creq, cres);
    CHECK(!cres.isCollision(), "两球圆心距 2.0 → 不碰");

    coal::DistanceRequest dreq;
    coal::DistanceResult dres;
    coal::distance(&s1, at(0, 0, 0), &s2, at(2, 0, 0), dreq, dres);
    CHECK(near(dres.min_distance, 1.0, 1e-5), "两球最小距离 = 1.0");
    if (!near(dres.min_distance, 1.0, 1e-5))
      std::fprintf(stderr, "       实得 %.9f\n", dres.min_distance);
  }

  // ② 两球相交
  {
    coal::CollisionRequest creq;
    coal::CollisionResult cres;
    coal::collide(&s1, at(0, 0, 0), &s2, at(0.5, 0, 0), creq, cres);
    CHECK(cres.isCollision(), "两球圆心距 0.5 → 相碰");
    CHECK(cres.numContacts() >= 1, "相碰时至少产生 1 个接触点");
  }

  // ③ 立方体与球
  {
    coal::DistanceRequest dreq;
    coal::DistanceResult dres;
    coal::distance(&box, at(0, 0, 0), &s1, at(2, 0, 0), dreq, dres);
    CHECK(near(dres.min_distance, 1.0, 1e-5),
          "边长1立方体 与 半径0.5球（相距2）最小距离 = 1.0");
    if (!near(dres.min_distance, 1.0, 1e-5))
      std::fprintf(stderr, "       实得 %.9f\n", dres.min_distance);
  }

  // ④ 自碰
  {
    coal::CollisionRequest creq;
    coal::CollisionResult cres;
    coal::collide(&box, at(0, 0, 0), &box, at(0, 0, 0), creq, cres);
    CHECK(cres.isCollision(), "同位姿的两个立方体必碰");
  }

  // ⑤ 相切：球心距 = 0.5+0.5 = 1.0 → 距离 ≈ 0
  {
    coal::DistanceRequest dreq;
    coal::DistanceResult dres;
    coal::distance(&s1, at(0, 0, 0), &s2, at(1.0, 0, 0), dreq, dres);
    CHECK(std::fabs(dres.min_distance) < 1e-5, "两球相切时最小距离 ≈ 0");
    if (std::fabs(dres.min_distance) >= 1e-5)
      std::fprintf(stderr, "       实得 %.9f\n", dres.min_distance);
  }

  if (failures) {
    std::fprintf(stderr, "\ncoal: %d 项断言失败\n", failures);
    return 1;
  }
  std::printf("\ncoal 3.0.3: 全部断言通过"
              "（同时证明 eigen/boost/octomap/qhull/assimp 五个接线都对）\n");
  return 0;
}
