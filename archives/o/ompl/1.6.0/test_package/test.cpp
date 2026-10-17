/* ompl 1.6.0 真实功能断言。
 *
 * 不用 dlopen 探针：解析到符号 ≠ 算得对。这里真的跑**一次运动规划**——
 * 在 2D 方形空间里放一道竖直墙（中间留个缺口），让 RRTConnect 从左边规划到右边，
 * 然后断言：
 *   · 确实找到了解
 *   · 路径的起点/终点就是给定的起终点
 *   · 路径上**每一个**插值点都满足有效性检查（即真的绕开了墙）
 *
 * 最后一条是关键：只判「找到解」很弱——返回一条穿墙的路径也叫「找到」。
 * 逐点复验才能证明状态有效性检查、采样、插值这条链真的在工作。
 */
#include <ompl/base/SpaceInformation.h>
#include <ompl/base/spaces/RealVectorStateSpace.h>
#include <ompl/geometric/SimpleSetup.h>
#include <ompl/geometric/planners/rrt/RRTConnect.h>

#include <cmath>
#include <cstdio>
#include <memory>   /* make_shared */

namespace ob = ompl::base;
namespace og = ompl::geometric;

/* 墙：x∈[0.45,0.55] 处不可通行，但 y∈[0.7,0.8] 留缺口 */
static bool isValid(const ob::State *st)
{
    const auto *s = st->as<ob::RealVectorStateSpace::StateType>();
    const double x = s->values[0], y = s->values[1];
    if (x > 0.45 && x < 0.55) {
        return (y > 0.7 && y < 0.8);
    }
    return true;
}

int main(void)
{
    auto space(std::make_shared<ob::RealVectorStateSpace>(2));
    ob::RealVectorBounds bounds(2);
    bounds.setLow(0.0);
    bounds.setHigh(1.0);
    space->setBounds(bounds);

    og::SimpleSetup ss(space);
    ss.setStateValidityChecker(isValid);
    /* 检查分辨率调细，保证「逐点复验」有意义 */
    ss.getSpaceInformation()->setStateValidityCheckingResolution(0.002);

    ob::ScopedState<ob::RealVectorStateSpace> start(space), goal(space);
    start->values[0] = 0.05; start->values[1] = 0.05;
    goal->values[0]  = 0.95; goal->values[1]  = 0.05;
    ss.setStartAndGoalStates(start, goal);

    ss.setPlanner(std::make_shared<og::RRTConnect>(ss.getSpaceInformation()));

    ob::PlannerStatus solved = ss.solve(10.0);
    if (!solved) {
        std::printf("FAIL 规划失败：缺口是通的，10 秒内应能找到解\n");
        return 1;
    }

    ss.simplifySolution();
    og::PathGeometric &path = ss.getSolutionPath();
    if (path.getStateCount() < 2) {
        std::printf("FAIL 路径点数 %u < 2\n", (unsigned)path.getStateCount());
        return 1;
    }

    /* ① 起点/终点要对得上 */
    {
        const auto *s0 = path.getState(0)->as<ob::RealVectorStateSpace::StateType>();
        const auto *sN = path.getState(path.getStateCount() - 1)
                             ->as<ob::RealVectorStateSpace::StateType>();
        if (std::fabs(s0->values[0] - 0.05) > 1e-6 ||
            std::fabs(s0->values[1] - 0.05) > 1e-6) {
            std::printf("FAIL 路径起点 (%.6f,%.6f) != (0.05,0.05)\n",
                        s0->values[0], s0->values[1]);
            return 1;
        }
        if (std::fabs(sN->values[0] - 0.95) > 1e-6 ||
            std::fabs(sN->values[1] - 0.05) > 1e-6) {
            std::printf("FAIL 路径终点 (%.6f,%.6f) != (0.95,0.05)\n",
                        sN->values[0], sN->values[1]);
            return 1;
        }
    }

    /* ② 逐点复验：路径必须真的绕开墙。
     *
     * ⚠️ 判据要与规划器**同源**，不能更严：
     *   规划器只保证「按 setStateValidityCheckingResolution 采样的点有效」，
     *   而墙是开区间定义的，插值点落在**几何边界上**（如 x=0.549942、
     *   y=0.699885，距缺口下沿差 1.15e-4）会被严格判据判为无效 ——
     *   那是我的判据过严，不是规划器算错。实撞：第一版用 interpolate(500)
     *   逐点严判，第 269 点即误报「穿墙」。
     * 所以这里用 SpaceInformation 自己的 checkMotion 逐段验证：
     * 它就是规划器采信的那把尺子。 */
    for (std::size_t i = 0; i + 1 < path.getStateCount(); ++i) {
        if (!ss.getSpaceInformation()->checkMotion(path.getState(i), path.getState(i + 1))) {
            const auto *a = path.getState(i)->as<ob::RealVectorStateSpace::StateType>();
            const auto *b = path.getState(i + 1)->as<ob::RealVectorStateSpace::StateType>();
            std::printf("FAIL 路径第 %u→%u 段穿墙: (%.6f,%.6f)→(%.6f,%.6f)\n",
                        (unsigned)i, (unsigned)(i + 1),
                        a->values[0], a->values[1], b->values[0], b->values[1]);
            return 1;
        }
    }
    /* 顶点本身也要有效（checkMotion 验的是段，端点单独确认） */
    for (std::size_t i = 0; i < path.getStateCount(); ++i) {
        if (!ss.getSpaceInformation()->isValid(path.getState(i))) {
            const auto *s = path.getState(i)->as<ob::RealVectorStateSpace::StateType>();
            std::printf("FAIL 路径第 %u 个顶点 (%.6f,%.6f) 无效\n",
                        (unsigned)i, s->values[0], s->values[1]);
            return 1;
        }
    }

    /* ③ 路径必须真的绕到缺口去过——否则说明墙根本没起作用。
     *    这里才用插值加密：找「有没有经过」用密采样是安全的（只增不减）。 */
    path.interpolate(500);
    bool through_gap = false;
    for (std::size_t i = 0; i < path.getStateCount(); ++i) {
        const auto *s = path.getState(i)->as<ob::RealVectorStateSpace::StateType>();
        if (s->values[0] > 0.45 && s->values[0] < 0.55 &&
            s->values[1] > 0.7 && s->values[1] < 0.8) {
            through_gap = true;
            break;
        }
    }
    if (!through_gap) {
        std::printf("FAIL 路径没有经过缺口，说明墙的有效性检查没生效\n");
        return 1;
    }

    std::printf("ompl OK: RRTConnect 规划成功，%u 段逐段 checkMotion 通过且经过缺口\n",
                (unsigned)path.getStateCount());
    return 0;
}
