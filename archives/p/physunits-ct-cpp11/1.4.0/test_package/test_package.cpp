#include <cmath>
#include <iostream>
#include <string>

#include "phys/units/io.hpp"
#include "phys/units/quantity_io_joule.hpp"
#include "phys/units/quantity_io_newton.hpp"

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
    using namespace phys::units::literals;

    int failures = 0;

    quantity<speed_d> speed = 45_km / hour;
    failures += check(std::fabs(magnitude(speed) - 12.5) < 1e-12,
                      "45_km / hour has magnitude 12.5 m/s");

    quantity<force_d> force{2_N};
    quantity<length_d> distance{2_m};
    quantity<energy_d> work = force * distance;
    failures += check(std::fabs(magnitude(work) - 4.0) < 1e-12,
                      "force multiplied by distance has magnitude 4");
    failures += check(to_unit_symbol(work) == "J",
                      "energy quantity uses the joule unit symbol");
    failures += check(io::to_string(work) == "4 J",
                      "energy quantity formats as 4 J");

    auto length_sum = 2_m + 3_m;
    failures += check(std::fabs(magnitude(length_sum) - 5.0) < 1e-12,
                      "compatible quantities can be added");

    auto duration = 2_min + 30_s;
    failures += check(std::fabs(magnitude(duration) - 150.0) < 1e-12,
                      "scaled time literals can be combined");

    if (failures != 0) {
        std::cerr << failures << " consumer checks failed" << std::endl;
        return 1;
    }

    std::cout << "PhysUnits consumer checks passed: 6" << std::endl;
    return 0;
}
