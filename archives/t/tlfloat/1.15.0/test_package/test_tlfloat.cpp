#include <cmath>
#include <cstdio>
#include <cstring>
#include <iostream>

#include <tlfloat/tlfloat.h>
#include <tlfloat/tlfloat.hpp>

int main() {
  int failures = 0;
  auto check = [&failures](bool condition, const char *name) {
    if (!condition) {
      std::cerr << "FAIL: " << name << '\n';
      ++failures;
    }
  };

  check(tlfloat_version() == 1015000ULL, "version");

  using tlfloat::Double;
  using tlfloat::Float;
  const Float sum = Float(1.25f) + Float(2.5f);
  const Float product = Float(1.5f) * Float(4.0f);
  check(static_cast<float>(sum) == 3.75f, "Float addition");
  check(static_cast<float>(product) == 6.0f, "Float multiplication");

  const Double quotient = Double(7.5) / Double(2.5);
  check(static_cast<double>(quotient) == 3.0, "Double division");
  check(Double(4.0) > Double(3.0), "comparison");
  const auto finite = Double(3.0).getUnpacked();
  check(!finite.isinf && !finite.isnan, "finite classification");

  char buffer[64] = {};
  const int length = tlfloat_snprintf(buffer, sizeof(buffer), "%g", 42.0);
  check(length > 0 && std::strstr(buffer, "42") != nullptr, "C printf API");

  check(!std::isnan(static_cast<double>(Double::flt_epsilon())), "epsilon");
  return failures == 0 ? 0 : 1;
}
