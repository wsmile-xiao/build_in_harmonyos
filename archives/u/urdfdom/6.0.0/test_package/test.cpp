#include <stdint.h>
#include <stddef.h>
#include <urdf_parser/urdf_parser.h>

#include <cmath>
#include <cstdio>
#include <string>

// urdfdom 6.0.0 —— 真实 URDF 解析验证（非 dlopen 空壳）。
// 这个包同时是三个依赖接线是否正确的**端到端证据**：
//   parseURDF 内部要用 tinyxml2 解析 XML、用 console_bridge 打日志、
//   用 urdfdom_headers 的类型承载模型。任一接线错了，这里都过不去。
// 断言：
//   ① 解析一段两连杆一转动关节的 URDF 成功
//   ② 模型名 / 连杆数 / 关节数
//   ③ 关节类型、父子连杆名、关节原点位姿（数值对账）
//   ④ 惯性参数（质量、ixx）读得对
//   ⑤ 关节限位读得对
//   ⑥ 错误路径：畸形 URDF 必须返回空指针

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

static const char *kUrdf = R"URDF(<?xml version="1.0"?>
<robot name="probe_arm">
  <link name="base_link">
    <inertial>
      <mass value="2.5"/>
      <origin xyz="0 0 0.1"/>
      <inertia ixx="0.05" ixy="0" ixz="0" iyy="0.06" iyz="0" izz="0.07"/>
    </inertial>
  </link>
  <link name="link1"/>
  <joint name="joint1" type="revolute">
    <parent link="base_link"/>
    <child link="link1"/>
    <origin xyz="0.3 0 0.2" rpy="0 0 1.5707963267948966"/>
    <axis xyz="0 0 1"/>
    <limit lower="-1.57" upper="1.57" effort="100" velocity="2.0"/>
  </joint>
</robot>
)URDF";

int main() {
  // ① ②
  urdf::ModelInterfaceSharedPtr model = urdf::parseURDF(kUrdf);
  CHECK(model != nullptr, "parseURDF 解析合法 URDF 成功");
  if (!model) {
    std::fprintf(stderr, "\nurdfdom: 解析失败，后续断言无法进行\n");
    return 1;
  }

  CHECK(model->getName() == "probe_arm", "模型名为 probe_arm");

  std::vector<urdf::LinkSharedPtr> links;
  model->getLinks(links);
  CHECK(links.size() == 2, "连杆数 = 2");
  if (links.size() != 2) std::fprintf(stderr, "       实得 %zu\n", links.size());
  CHECK(model->joints_.size() == 1, "关节数 = 1");

  CHECK(model->getRoot() != nullptr && model->getRoot()->name == "base_link",
        "根连杆为 base_link");

  // ③ 关节
  urdf::JointConstSharedPtr j = model->getJoint("joint1");
  CHECK(j != nullptr, "按名字取到 joint1");
  if (j) {
    CHECK(j->type == urdf::Joint::REVOLUTE, "关节类型为 REVOLUTE");
    CHECK(j->parent_link_name == "base_link" && j->child_link_name == "link1",
          "父/子连杆名正确");
    const urdf::Vector3 &p = j->parent_to_joint_origin_transform.position;
    CHECK(near(p.x, 0.3) && near(p.y, 0.0) && near(p.z, 0.2),
          "关节原点 xyz = (0.3, 0, 0.2)");
    double r = 0, pi = 0, y = 0;
    j->parent_to_joint_origin_transform.rotation.getRPY(r, pi, y);
    CHECK(near(y, 1.5707963267948966, 1e-9), "关节原点 yaw = pi/2");
    if (!near(y, 1.5707963267948966, 1e-9))
      std::fprintf(stderr, "       实得 yaw=%.12f\n", y);
    CHECK(near(j->axis.z, 1.0) && near(j->axis.x, 0.0), "关节轴 = (0,0,1)");

    // ⑤ 限位
    CHECK(j->limits != nullptr, "关节带 limits");
    if (j->limits) {
      CHECK(near(j->limits->lower, -1.57) && near(j->limits->upper, 1.57),
            "限位 lower/upper = -1.57 / 1.57");
      CHECK(near(j->limits->effort, 100.0) && near(j->limits->velocity, 2.0),
            "限位 effort/velocity = 100 / 2.0");
    }
  }

  // ④ 惯性
  urdf::LinkConstSharedPtr base = model->getLink("base_link");
  CHECK(base != nullptr, "按名字取到 base_link");
  if (base) {
    CHECK(base->inertial != nullptr, "base_link 带 inertial");
    if (base->inertial) {
      CHECK(near(base->inertial->mass, 2.5), "质量 = 2.5");
      CHECK(near(base->inertial->ixx, 0.05) && near(base->inertial->izz, 0.07),
            "惯性张量 ixx=0.05 izz=0.07");
      CHECK(near(base->inertial->origin.position.z, 0.1), "惯性原点 z = 0.1");
    }
  }

  // ⑥ 错误路径
  {
    urdf::ModelInterfaceSharedPtr bad = urdf::parseURDF("<robot><link name=");
    CHECK(bad == nullptr, "畸形 URDF 返回空指针");
  }

  if (failures) {
    std::fprintf(stderr, "\nurdfdom: %d 项断言失败\n", failures);
    return 1;
  }
  std::printf("\nurdfdom 6.0.0: 全部断言通过"
              "（同时证明 console_bridge / tinyxml2 / urdfdom_headers 三个接线都对）\n");
  return 0;
}
