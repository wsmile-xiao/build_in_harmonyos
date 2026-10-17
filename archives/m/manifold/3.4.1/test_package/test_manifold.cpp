// Consumer test for manifold/3.4.1.
// Constructs a Cube and a Sphere via the public C++ API and asserts the
// resulting manifold is error-free and has positive volume. Returns non-zero
// on any failed assertion so the harness can detect a real failure.
#include <cstdio>

#include "manifold/common.h"
#include "manifold/cross_section.h"
#include "manifold/manifold.h"

int failures = 0;

#define CHECK(cond)                                                        \
  do {                                                                     \
    if (!(cond)) {                                                         \
      std::printf("FAIL (line %d): %s\n", __LINE__, #cond);                \
      ++failures;                                                          \
    }                                                                      \
  } while (0)

int main() {
  // Cube with explicit size (default-center), volume = 2*2*2 = 8.
  manifold::Manifold cube = manifold::Manifold::Cube({2.0, 2.0, 2.0});
  CHECK(cube.Status() == manifold::Manifold::Error::NoError);
  CHECK(cube.Volume() > 0.0);

  // Sphere with explicit radius/segments.
  manifold::Manifold sphere = manifold::Manifold::Sphere(1.0, 32);
  CHECK(sphere.Status() == manifold::Manifold::Error::NoError);
  CHECK(sphere.Volume() > 0.0);

  // CrossSection (2D) path is enabled by default (MANIFOLD_CROSS_SECTION=ON);
  // build+link of a 2D section from the cube confirms it too.
  manifold::CrossSection cs = manifold::CrossSection::Square({2.0, 2.0});
  CHECK(cs.Area() > 0.0);

  if (failures == 0) {
    std::printf("test_manifold: all checks passed\n");
  } else {
    std::printf("test_manifold: %d check(s) failed\n", failures);
  }
  return failures > 0 ? 1 : 0;
}
