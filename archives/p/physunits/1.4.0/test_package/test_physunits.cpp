// test_physunits — 消费者测试 (R34: 真实调用被测库 physunits API)
// 覆盖: 量纲化字面量、编译期量纲加法/乘除法、单位常量换算 .to(unit)、magnitude()
#include "phys/units/quantity.hpp"

#include <cmath>

using namespace phys::units;
using namespace phys::units::literals;

int main()
{
    // 1) 同量纲加法 (编译期量纲一致性校验)
    quantity<length_d> c = 2.0_m + 3.0_m;
    if (std::fabs(c.magnitude() - 5.0) > 1e-12) return 1;

    // 2) 派生量纲: m/s (速度)
    auto speed = 100.0_m / 20.0_s;
    if (std::fabs(speed.magnitude() - 5.0) > 1e-12) return 2;

    // 3) 量纲乘法: m * m (面积)
    auto area = 2.0_m * 3.0_m;
    if (std::fabs(area.magnitude() - 6.0) > 1e-12) return 3;

    // 4) 单位换算: 3600 s -> hour (库提供的非 SI 单位常量)
    //    注: 默认 PHYS_UNITS_COLLAPSE_TO_REP=1, 无量纲结果直接折叠为 double
    auto hours = (3600.0_s).to(hour);
    if (std::fabs(hours - 1.0) > 1e-12) return 4;

    return 0;
}
