#include <cstdlib>
#include <iostream>
#include <string>

#include "phys/units/quantity.hpp"
#include "phys/units/io.hpp"
#include "phys/units/quantity_io_joule.hpp"
#include "phys/units/quantity_io_meter.hpp"
#include "phys/units/quantity_io_newton.hpp"
#include "phys/units/quantity_io_ohm.hpp"
#include "phys/units/quantity_io_second.hpp"
#include "phys/units/quantity_io_volt.hpp"
#include "phys/units/other_units.hpp"

namespace {

int check(bool condition, const char *message)
{
    if (!condition) {
        std::cerr << "FAIL: " << message << std::endl;
        return 1;
    }
    return 0;
}

}  // namespace

int main()
{
    using namespace phys::units;
    using namespace phys::units::io;

    int failures = 0;

    // work = force * distance (README 的核心示例)
    quantity<force_d> force(2.0 * newton());
    quantity<length_d> dx(2.0 * meter());
    quantity<energy_d> work = force * dx;
    failures += check(to_magnitude(work) == "4",
                      "2 N * 2 m has magnitude 4");
    failures += check(to_unit_symbol(work) == "J",
                      "energy quantity uses the joule unit symbol");
    failures += check(to_magnitude(work) + " " + to_unit_symbol(work) == "4 J",
                      "energy quantity formats as '4 J'");

    // 前缀函数组合（C++98 无 UDL 字面量，README 的 speed 示例）
    quantity<speed_d> speed = 45 * kilo() * meter() / second();
    failures += check(std::atof(to_magnitude(speed).c_str()) == 45000.0,
                      "45 * kilo() * m / s has magnitude 45000");
    failures += check(to_unit_symbol(speed) == "m/s",
                      "speed quantity uses the m/s unit symbol");

    // n 次幂/n 次根的编译期量纲运算
    quantity<area_d> area = nth_power<2>(meter());
    failures += check(std::atof(to_magnitude(area).c_str()) == 1.0,
                      "nth_power<2>(meter()) has magnitude 1");

    // 工程记数（README 的电阻示例：4.7 kOhm）
    quantity<electric_resistance_d> resistance(4.7 * kilo() * volt() / ampere());
    failures += check(io::eng::to_string(resistance) == "4.7 kOhm",
                      "engineering notation formats 4.7 kV / A as '4.7 kOhm'");

    if (failures != 0) {
        std::cerr << failures << " consumer checks failed" << std::endl;
        return 1;
    }

    std::cout << "PhysUnits-CT consumer checks passed: 6" << std::endl;
    return 0;
}
