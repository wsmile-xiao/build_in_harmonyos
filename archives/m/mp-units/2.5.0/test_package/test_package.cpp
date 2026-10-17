#include <mp-units/ext/format.h>
#include <mp-units/systems/isq.h>
#include <mp-units/systems/si.h>

#include <iostream>
#include <string>

using namespace mp_units;
using namespace mp_units::si::unit_symbols;

constexpr auto average_speed(QuantityOf<isq::distance> auto distance,
                             QuantityOf<isq::duration> auto duration)
{
  return distance / duration;
}

int main()
{
  constexpr auto speed = average_speed(240 * km, 2 * h);

  // Compile-time dimensional arithmetic and unit conversion.
  static_assert(speed.numerical_value_in(km / h) == 120);

  if (speed.numerical_value_in(km / h) != 120)
    return 1;

  const std::string formatted = MP_UNITS_STD_FMT::format("{}", speed);
  if (formatted.find("120") == std::string::npos)
    return 2;

  if (MP_UNITS_STD_FMT::format("{}", 2 * m).find("2") == std::string::npos)
    return 3;

  std::cout << "mp-units OK: " << formatted << '\n';
  return 0;
}
