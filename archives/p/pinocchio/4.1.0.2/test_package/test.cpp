// pinocchio 4.1.0 —— 真实刚体动力学计算验证（非链接空壳）。
//
// 判据取自可手算的机构：一条纯转动关节链，各连杆沿 X 轴串联。
//   · 模型维度：n 个 revolute 关节 → nq == nv == n（转动关节各占 1 维）
//   · 零位前向运动学：末端位置 = 各连杆长度之和（沿 X）
//   · 转 90° 后：第二段折向 Y，末端 X 坐标缩短——**证明角度真的参与了计算**
// 最后一条是关键：只验零位的话，一个「把关节位移全当 0」的实现也能蒙混过关。
//
// 头名逐个核对过上游 include/ 的实际布局，**没有按包名猜**：
//   · 生成器占位写的 <pinocchio.h> 不存在；
//   · 4.1.0 已把 multibody/model.hpp 挪进 deprecated/，正路是聚合头 pinocchio/multibody.hpp。
// 本批两次栽在猜头名上（brotli 的 <brotli.h> 同源），故这条已写进生成器的测试模板。
#include "pinocchio/multibody.hpp"
#include "pinocchio/algorithm/joint-configuration.hpp"
#include "pinocchio/algorithm/kinematics.hpp"

#include <cmath>
#include <cstdio>

static int failures = 0;
#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            std::fprintf(stderr, "[FAIL] %s  (%s:%d)\n", msg, __FILE__,        \
                         __LINE__);                                            \
            ++failures;                                                        \
        } else {                                                               \
            std::printf("[ok] %s\n", msg);                                     \
        }                                                                      \
    } while (0)

static bool near(double a, double b, double eps = 1e-9) {
    return std::fabs(a - b) < eps;
}

int main() {
    using namespace pinocchio;

    const double L = 0.5;          // 每段连杆长度
    const int N = 3;               // 关节数

    Model model;
    JointIndex parent = 0;
    for (int i = 0; i < N; ++i) {
        // 每段沿父连杆的 X 轴平移 L，关节绕 Z 轴转动
        SE3 placement = SE3::Identity();
        placement.translation()[0] = (i == 0 ? 0.0 : L);
        char name[32];
        std::snprintf(name, sizeof(name), "joint_%d", i);
        parent = model.addJoint(parent, JointModelRZ(), placement, name);
        model.appendBodyToJoint(parent, Inertia::Identity(), SE3::Identity());
    }
    // 末端再加一个固定坐标系，沿 X 偏移 L
    SE3 tip = SE3::Identity();
    tip.translation()[0] = L;

    CHECK(model.njoints == N + 1, "njoints == 关节数 + 1（含 universe）");
    CHECK(model.nq == N, "nq == 3（三个转动关节各 1 维）");
    CHECK(model.nv == N, "nv == 3");

    Data data(model);

    // ① 零位：末端应在 X = 2L（两段 L 平移）+ tip 的 L = 3L
    Eigen::VectorXd q = Eigen::VectorXd::Zero(model.nq);
    forwardKinematics(model, data, q);
    const SE3 &last = data.oMi[N];
    double x0 = (last * tip).translation()[0];
    double y0 = (last * tip).translation()[1];
    std::printf("     零位末端: x=%.9f y=%.9f\n", x0, y0);
    CHECK(near(x0, 3 * L), "零位末端 X == 3L（各段沿 X 串联）");
    CHECK(near(y0, 0.0), "零位末端 Y == 0");

    // ② 第二个关节转 90°：末端应折向 Y，X 缩短 —— 证明 q 真的参与了计算
    q.setZero();
    q[1] = M_PI / 2.0;
    forwardKinematics(model, data, q);
    const SE3 &last2 = data.oMi[N];
    double x1 = (last2 * tip).translation()[0];
    double y1 = (last2 * tip).translation()[1];
    std::printf("     转 90° 后末端: x=%.9f y=%.9f\n", x1, y1);
    CHECK(near(x1, L), "转 90° 后末端 X == L（后两段折走了）");
    CHECK(near(y1, 2 * L), "转 90° 后末端 Y == 2L（折向 Y）");

    if (failures) {
        std::fprintf(stderr, "\npinocchio: %d 项断言失败\n", failures);
        return 1;
    }
    std::printf("\npinocchio 4.1.0: 全部断言通过（模型维度 + 前向运动学）\n");
    return 0;
}
