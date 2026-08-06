/* orocos-kdl 1.5.1 真实功能断言。
 *
 * 不用 dlopen 探针：解析到符号 ≠ 算得对。这里真的跑**运动学正解**——
 * 造一个两连杆平面机械臂，让求解器算末端位姿，再跟解析解逐分量对账。
 * 平面两连杆的解析解是初等三角，可以精确写出来，所以能卡紧容差、
 * 而不是只看「没崩」。
 *
 * 顺带验 Eigen 集成：KDL 的 Rotation/Vector 底层用 Eigen，
 * 这条链通了才说明 eigen 依赖真的接上了。
 */
#include <kdl/chain.hpp>
#include <kdl/chainfksolverpos_recursive.hpp>
#include <kdl/frames.hpp>
#include <kdl/jntarray.hpp>

#include <cmath>
#include <cstdio>

int main(void)
{
    /* 两连杆平面臂：绕 Z 转，各沿 X 延伸 L1 / L2 */
    const double L1 = 2.0, L2 = 1.0;
    KDL::Chain chain;
    chain.addSegment(KDL::Segment(
        KDL::Joint(KDL::Joint::RotZ),
        KDL::Frame(KDL::Vector(L1, 0.0, 0.0))));
    chain.addSegment(KDL::Segment(
        KDL::Joint(KDL::Joint::RotZ),
        KDL::Frame(KDL::Vector(L2, 0.0, 0.0))));

    if (chain.getNrOfJoints() != 2) {
        std::printf("FAIL 关节数 %u != 2\n", chain.getNrOfJoints());
        return 1;
    }
    if (chain.getNrOfSegments() != 2) {
        std::printf("FAIL 段数 %u != 2\n", chain.getNrOfSegments());
        return 1;
    }

    KDL::ChainFkSolverPos_recursive fk(chain);

    /* ① 零位：末端应在 (L1+L2, 0, 0) */
    {
        KDL::JntArray q(2);
        q(0) = 0.0; q(1) = 0.0;
        KDL::Frame f;
        if (fk.JntToCart(q, f) < 0) {
            std::printf("FAIL 零位正解求解失败\n");
            return 1;
        }
        if (std::fabs(f.p.x() - (L1 + L2)) > 1e-12 ||
            std::fabs(f.p.y()) > 1e-12 || std::fabs(f.p.z()) > 1e-12) {
            std::printf("FAIL 零位末端 (%.12f,%.12f,%.12f) != (%.1f,0,0)\n",
                        f.p.x(), f.p.y(), f.p.z(), L1 + L2);
            return 1;
        }
    }

    /* ② q=(90°,0)：整条臂转到 +Y，末端应在 (0, L1+L2, 0) */
    {
        KDL::JntArray q(2);
        q(0) = M_PI / 2.0; q(1) = 0.0;
        KDL::Frame f;
        if (fk.JntToCart(q, f) < 0) {
            std::printf("FAIL q=(90,0) 正解求解失败\n");
            return 1;
        }
        if (std::fabs(f.p.x()) > 1e-9 ||
            std::fabs(f.p.y() - (L1 + L2)) > 1e-9) {
            std::printf("FAIL q=(90,0) 末端 (%.12f,%.12f) != (0,%.1f)\n",
                        f.p.x(), f.p.y(), L1 + L2);
            return 1;
        }
    }

    /* ③ 一般位形 q=(30°,60°)，与解析解逐分量对账：
     *    x = L1*cos(q0) + L2*cos(q0+q1)
     *    y = L1*sin(q0) + L2*sin(q0+q1)  */
    {
        const double q0 = M_PI / 6.0, q1 = M_PI / 3.0;
        KDL::JntArray q(2);
        q(0) = q0; q(1) = q1;
        KDL::Frame f;
        /* 返回值必须检查：求解失败时 f 保持默认构造的**恒等位姿**，
         * 后续断言比的就不是计算结果了 —— 要么报出误导性的数值 FAIL
         * （让人以为是精度问题），要么恰好接近而静默通过、掩盖真实故障。 */
        if (fk.JntToCart(q, f) < 0) {
            std::printf("FAIL q=(30,60) 正解求解失败\n");
            return 1;
        }
        const double ex = L1 * std::cos(q0) + L2 * std::cos(q0 + q1);
        const double ey = L1 * std::sin(q0) + L2 * std::sin(q0 + q1);
        if (std::fabs(f.p.x() - ex) > 1e-9 || std::fabs(f.p.y() - ey) > 1e-9) {
            std::printf("FAIL q=(30,60) 末端 (%.12f,%.12f) != 解析解 (%.12f,%.12f)\n",
                        f.p.x(), f.p.y(), ex, ey);
            return 1;
        }
        /* 末端姿态应绕 Z 转了 q0+q1 */
        double r, pch, yaw;
        f.M.GetRPY(r, pch, yaw);
        if (std::fabs(yaw - (q0 + q1)) > 1e-9) {
            std::printf("FAIL 末端 yaw %.12f != %.12f\n", yaw, q0 + q1);
            return 1;
        }
        /* 两个关节都绕 Z 转，末端必须仍在 XY 平面内：roll/pitch 应为 0。
         * 只验 yaw 是不够的——若旋转的合成出了错（比如轴向串了），
         * yaw 仍可能对，而姿态已经翻出平面。 */
        if (std::fabs(r) > 1e-9 || std::fabs(pch) > 1e-9) {
            std::printf("FAIL 末端 roll=%.12f pitch=%.12f，绕 Z 的平面臂应均为 0\n",
                        r, pch);
            return 1;
        }
    }

    /* ④ 旋转与其逆相乘应得单位阵——验 Rotation 的运算闭合性 */
    {
        KDL::Rotation R = KDL::Rotation::RPY(0.3, -0.7, 1.1);
        KDL::Rotation I = R * R.Inverse();
        for (int i = 0; i < 3; ++i)
            for (int j = 0; j < 3; ++j) {
                const double want = (i == j) ? 1.0 : 0.0;
                if (std::fabs(I(i, j) - want) > 1e-12) {
                    std::printf("FAIL R*R^-1 的 (%d,%d) = %.12f，应为 %.1f\n",
                                i, j, I(i, j), want);
                    return 1;
                }
            }
    }

    std::printf("orocos-kdl OK: 正解 3 例与解析解吻合(<1e-9) + 姿态/旋转闭合性\n");
    return 0;
}
