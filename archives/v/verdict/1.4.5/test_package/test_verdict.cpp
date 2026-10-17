// test_package/test_verdict.cpp — verdict 1.4.5 consumer checks on OHOS aarch64.
//
// Uses only the packaged public header (include/verdict.h + verdict_config.h)
// and libverdict.a. Every check calls the real metrics API: eight element
// geometries with analytically known quality values, plus two comparative
// checks that a degenerate element is scored worse than a regular one.
#include "verdict.h"

#include <cmath>
#include <cstdio>

namespace {

int g_checks = 0;
int g_failures = 0;

void check(bool condition, const char* what)
{
  ++g_checks;
  if (!condition) {
    ++g_failures;
    std::printf("FAIL: %s\n", what);
  }
}

bool near(double actual, double expected, double tol)
{
  return std::fabs(actual - expected) <= tol;
}

}  // namespace

int main()
{
  // 1. edge_length: 3-4-5 right triangle leg.
  {
    const double nodes[2][3] = { { 0, 0, 0 }, { 3, 4, 0 } };
    check(near(verdict::edge_length(2, nodes), 5.0, 1e-9), "edge_length == 5");
  }

  // 2. tri_area: unit right triangle.
  {
    const double nodes[3][3] = { { 0, 0, 0 }, { 1, 0, 0 }, { 0, 1, 0 } };
    check(near(verdict::tri_area(3, nodes), 0.5, 1e-9), "tri_area == 0.5");
  }

  // 3. quad_area: unit square.
  {
    const double nodes[4][3] = { { 0, 0, 0 }, { 1, 0, 0 }, { 1, 1, 0 }, { 0, 1, 0 } };
    check(near(verdict::quad_area(4, nodes), 1.0, 1e-9), "quad_area == 1");
  }

  // 4. tet_volume: unit right tetrahedron.
  {
    const double nodes[4][3] = { { 0, 0, 0 }, { 1, 0, 0 }, { 0, 1, 0 }, { 0, 0, 1 } };
    check(near(verdict::tet_volume(4, nodes), 1.0 / 6.0, 1e-9), "tet_volume == 1/6");
  }

  // 5. hex_volume: unit cube.
  {
    const double nodes[8][3] = { { 0, 0, 0 }, { 1, 0, 0 }, { 1, 1, 0 }, { 0, 1, 0 },
                                 { 0, 0, 1 }, { 1, 0, 1 }, { 1, 1, 1 }, { 0, 1, 1 } };
    check(near(verdict::hex_volume(8, nodes), 1.0, 1e-9), "hex_volume == 1");
  }

  // 6. wedge_volume: unit triangular prism.
  {
    const double nodes[6][3] = { { 0, 0, 0 }, { 1, 0, 0 }, { 0, 1, 0 },
                                 { 0, 0, 1 }, { 1, 0, 1 }, { 0, 1, 1 } };
    check(near(verdict::wedge_volume(6, nodes), 0.5, 1e-9), "wedge_volume == 0.5");
  }

  // 7. pyramid_volume: unit square base, apex above the center.
  {
    const double nodes[5][3] = { { 0, 0, 0 }, { 1, 0, 0 }, { 1, 1, 0 }, { 0, 1, 0 },
                                 { 0.5, 0.5, 1 } };
    check(near(verdict::pyramid_volume(5, nodes), 1.0 / 3.0, 1e-9), "pyramid_volume == 1/3");
  }

  const double equilateral[3][3] = { { 0, 0, 0 }, { 1, 0, 0 },
                                     { 0.5, std::sqrt(3.0) / 2.0, 0 } };
  const double sliver[3][3] = { { 0, 0, 0 }, { 1, 0, 0 }, { 0.5, 1e-3, 0 } };

  // 8. tri_minimum_angle: equilateral angle beats sliver angle.
  check(verdict::tri_minimum_angle(3, equilateral) >
        verdict::tri_minimum_angle(3, sliver),
        "tri_minimum_angle(equilateral) > sliver");

  // 9. tri_scaled_jacobian: equilateral beats sliver.
  check(verdict::tri_scaled_jacobian(3, equilateral) >
        verdict::tri_scaled_jacobian(3, sliver),
        "tri_scaled_jacobian(equilateral) > sliver");

  // 10. tet_radius_ratio: regular tetrahedron scores the ideal 1.
  {
    const double regular[4][3] = { { 0, 0, 0 }, { 1, 0, 0 },
                                   { 0.5, std::sqrt(3.0) / 2.0, 0 },
                                   { 0.5, std::sqrt(3.0) / 6.0, std::sqrt(6.0) / 3.0 } };
    check(near(verdict::tet_radius_ratio(4, regular), 1.0, 1e-9),
          "tet_radius_ratio(regular) == 1");
  }

  std::printf("verdict consumer checks: %d/%d passed\n",
              g_checks - g_failures, g_checks);
  return g_failures == 0 ? 0 : 1;
}
