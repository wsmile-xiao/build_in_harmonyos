/*
 * End-to-end installed-package workflow for HarmonyOS.
 *
 * The calculation models a small monthly savings projection.  It intentionally
 * uses the exported C++ numeric type and the exported C formatting API in one
 * consumer process, instead of only checking individual API contracts.
 */
#include <cmath>
#include <cstdio>

#include <tlfloat/tlfloat.h>
#include <tlfloat/tlfloat.hpp>

int main() {
  using tlfloat::Double;

  const Double monthly_deposit(125.0);
  const Double monthly_rate(0.0025);
  Double balance(1000.0);

  for (int month = 0; month < 36; ++month) {
    balance = balance * (Double(1.0) + monthly_rate) + monthly_deposit;
  }

  const double projected_balance = static_cast<double>(balance);
  char report[128] = {};
  const int written = tlfloat_snprintf(
      report,
      sizeof(report),
      "workflow: 36-month projected balance %.2f",
      projected_balance);

  if (!std::isfinite(projected_balance) || projected_balance <= 5500.0 ||
      written <= 0 || written >= static_cast<int>(sizeof(report))) {
    std::fprintf(stderr, "workflow: unable to produce a valid projection\n");
    return 1;
  }

  std::puts(report);
  return 0;
}
