/* fcl 0.7.0 真实功能断言。
 *
 * 不用 dlopen 探针：解析到符号 ≠ 算得对。这里真的跑**碰撞检测与距离计算**——
 * 用两个盒子和两个球，断言相交与否、穿透深度、以及分离距离的**数值**。
 * 这些几何量都有解析解，可以精确对账。
 *
 * 同时这条链验证了 fcl 的两个关键依赖真的接上了：
 *   · libccd —— narrowphase 的 GJK/EPA 求解器
 *   · eigen  —— fcl 的向量/变换全部基于 Eigen
 */
#include <fcl/geometry/shape/box.h>
#include <fcl/geometry/shape/sphere.h>
#include <fcl/narrowphase/collision.h>
#include <fcl/narrowphase/collision_object.h>
#include <fcl/narrowphase/distance.h>

#include <cmath>
#include <cstdio>
#include <memory>

using S = double;

int main(void)
{
    /* ① 两个单位立方体，中心相距 0.5 —— 必然相交 */
    {
        auto b1 = std::make_shared<fcl::Box<S>>(1.0, 1.0, 1.0);
        auto b2 = std::make_shared<fcl::Box<S>>(1.0, 1.0, 1.0);
        fcl::Transform3<S> t1 = fcl::Transform3<S>::Identity();
        fcl::Transform3<S> t2 = fcl::Transform3<S>::Identity();
        t2.translation() = fcl::Vector3<S>(0.5, 0.0, 0.0);

        fcl::CollisionObject<S> o1(b1, t1), o2(b2, t2);
        fcl::CollisionRequest<S> req(1, true);
        fcl::CollisionResult<S> res;
        std::size_t n = fcl::collide(&o1, &o2, req, res);

        if (n == 0 || !res.isCollision()) {
            std::printf("FAIL 中心距 0.5 的两个单位立方体应相交，实判不相交\n");
            return 1;
        }
        /* 沿 x 重叠量 = 1 - 0.5 = 0.5 */
        const S depth = res.getContact(0).penetration_depth;
        if (std::fabs(depth - 0.5) > 1e-6) {
            std::printf("FAIL 穿透深度 %.12f != 0.5\n", (double)depth);
            return 1;
        }
    }

    /* ② 同样两个立方体，中心相距 2.0 —— 必然分离，且间隙 = 2.0 - 1.0 = 1.0 */
    {
        auto b1 = std::make_shared<fcl::Box<S>>(1.0, 1.0, 1.0);
        auto b2 = std::make_shared<fcl::Box<S>>(1.0, 1.0, 1.0);
        fcl::Transform3<S> t1 = fcl::Transform3<S>::Identity();
        fcl::Transform3<S> t2 = fcl::Transform3<S>::Identity();
        t2.translation() = fcl::Vector3<S>(2.0, 0.0, 0.0);

        fcl::CollisionObject<S> o1(b1, t1), o2(b2, t2);
        fcl::CollisionRequest<S> creq;
        fcl::CollisionResult<S> cres;
        if (fcl::collide(&o1, &o2, creq, cres) != 0) {
            std::printf("FAIL 中心距 2.0 应分离，实判相交\n");
            return 1;
        }

        fcl::DistanceRequest<S> dreq(true);
        fcl::DistanceResult<S> dres;
        /* 返回值就是最小距离，与写进 result 的那份对账 ——
         * 两条路径给出的值不一致说明库内部状态没同步好。 */
        const S ret = fcl::distance(&o1, &o2, dreq, dres);
        if (std::fabs(ret - dres.min_distance) > 1e-9) {
            std::printf("FAIL distance() 返回 %.12f 与 result.min_distance %.12f 不一致\n",
                        (double)ret, (double)dres.min_distance);
            return 1;
        }
        if (std::fabs(dres.min_distance - 1.0) > 1e-6) {
            std::printf("FAIL 分离距离 %.12f != 1.0\n", (double)dres.min_distance);
            return 1;
        }
    }

    /* ③ 两个球：半径 1.0 与 0.5，中心距 3.0 → 间隙 = 3.0 - 1.5 = 1.5。
     *    球走的是 libccd 的 GJK 路径，与盒子的分支不同，故单独验。 */
    {
        auto s1 = std::make_shared<fcl::Sphere<S>>(1.0);
        auto s2 = std::make_shared<fcl::Sphere<S>>(0.5);
        fcl::Transform3<S> t1 = fcl::Transform3<S>::Identity();
        fcl::Transform3<S> t2 = fcl::Transform3<S>::Identity();
        t2.translation() = fcl::Vector3<S>(3.0, 0.0, 0.0);

        fcl::CollisionObject<S> o1(s1, t1), o2(s2, t2);
        fcl::DistanceRequest<S> dreq(true);
        fcl::DistanceResult<S> dres;
        const S ret = fcl::distance(&o1, &o2, dreq, dres);
        if (std::fabs(ret - dres.min_distance) > 1e-9) {
            std::printf("FAIL 球-球 distance() 返回 %.12f 与 result.min_distance %.12f 不一致\n",
                        (double)ret, (double)dres.min_distance);
            return 1;
        }
        if (std::fabs(dres.min_distance - 1.5) > 1e-6) {
            std::printf("FAIL 两球间隙 %.12f != 1.5\n", (double)dres.min_distance);
            return 1;
        }
    }

    /* ④ 球相交：半径 1.0 与 1.0，中心距 1.5 → 相交，且距离为负或 0 */
    {
        auto s1 = std::make_shared<fcl::Sphere<S>>(1.0);
        auto s2 = std::make_shared<fcl::Sphere<S>>(1.0);
        fcl::Transform3<S> t1 = fcl::Transform3<S>::Identity();
        fcl::Transform3<S> t2 = fcl::Transform3<S>::Identity();
        t2.translation() = fcl::Vector3<S>(1.5, 0.0, 0.0);

        fcl::CollisionObject<S> o1(s1, t1), o2(s2, t2);
        fcl::CollisionRequest<S> req(1, true);
        fcl::CollisionResult<S> res;
        if (fcl::collide(&o1, &o2, req, res) == 0) {
            std::printf("FAIL 中心距 1.5 的两个单位球应相交\n");
            return 1;
        }
    }

    std::printf("fcl OK: 盒-盒 相交/穿透深度/分离距离 + 球-球 GJK 路径 共 4 例\n");
    return 0;
}
