// Consumer test for libhwy: exercises the real SIMD public API.
// 7 explicit Check() assertions: target mask, target name, lane count,
// vector load/arithmetic/store results, and inactive-lane preservation.
#include <cmath>
#include <cstdio>

#include "hwy/highway.h"
#include "hwy/targets.h"

namespace hn = hwy::HWY_NAMESPACE;

static int Check(bool condition, const char* message) {
  if (!condition) {
    std::fprintf(stderr, "FAIL: %s\n", message);
    return 1;
  }
  return 0;
}

int main() {
  int failures = 0;

  const int64_t supported = hwy::SupportedTargets();
  failures += Check(supported != 0, "SupportedTargets returns a non-zero mask");
  failures += Check(hwy::TargetName(HWY_SCALAR) != nullptr,
                    "TargetName resolves scalar target");

  const hn::CappedTag<float, 4> d;
  const size_t lanes = hn::Lanes(d);
  failures += Check(lanes >= 1 && lanes <= 4, "CappedTag lane count is valid");

  HWY_ALIGN float input[4] = {1.0f, 2.0f, 3.0f, 4.0f};
  HWY_ALIGN float output[4] = {0.0f, 0.0f, 0.0f, 0.0f};

  const auto loaded = hn::Load(d, input);
  const auto iota = hn::Iota(d, 1.0f);
  const auto sum = loaded + iota + hn::Set(d, 2.0f);
  hn::Store(sum, d, output);

  failures += Check(std::fabs(output[0] - 4.0f) < 0.001f,
                    "first lane stores loaded+iota+set result");
  if (lanes > 1) {
    failures += Check(std::fabs(output[1] - 6.0f) < 0.001f,
                      "second lane stores loaded+iota+set result");
  } else {
    failures += Check(output[1] == 0.0f, "inactive lane remains untouched");
  }
  failures += Check(output[lanes - 1] > 0.0f, "last active lane is written");
  failures += Check(lanes == 4 || output[lanes] == 0.0f,
                    "first inactive lane is untouched when present");

  if (failures != 0) {
    return 1;
  }

  std::printf("libhwy consumer checks passed\n");
  return 0;
}
